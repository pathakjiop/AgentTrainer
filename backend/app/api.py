import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, Request, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import current_user
from app.models.user import User, WorkspaceMember
from app.models.workspace import Workspace
from app.models.agent import Agent, AgentVersion
from app.models.knowledge import KnowledgeBase, AgentKnowledgeBase, Document, DocumentChunk
from app.models.chat import Conversation, Message
from app.models.dataset import Dataset, DatasetExample
from app.models.evaluation import EvaluationRun, EvaluationResult
from app.models.prompt_opt import PromptOptimization
from app.models.deployment import Deployment, ApiKey
from app.models.analytics import UsageEvent, AuditLog

from app.schemas import (
    UserCreate, LoginRequest, UserOut, TokenOut, PasswordResetRequest,
    WorkspaceCreate, WorkspaceOut, WorkspaceMemberOut, WorkspaceMemberAdd,
    AgentCreate, AgentUpdate, AgentOut, AgentVersionOut, PublishVersionRequest,
    KnowledgeBaseCreate, KnowledgeBaseOut, DocumentOut, DocumentChunkOut,
    RetrievalQuery, RetrievalResponse, RetrievalChunkOut,
    ConversationCreate, ConversationOut, MessageOut, ChatMessageInput,
    DatasetCreate, DatasetOut, DatasetExampleCreate, DatasetExampleOut, SyntheticExampleGenerateRequest,
    EvaluationRequest, EvaluationOut, BatchEvaluationRequest, EvaluationRunOut, EvaluationResultOut,
    PromptOptimizeRequest, PromptOptimizationOut,
    DeploymentCreate, DeploymentUpdate, DeploymentOut, ApiKeyCreate, ApiKeyOut, ApiKeyCreatedOut,
    PublicChatRequest, PublicChatResponse,
    UsageMetricsOut, AuditLogOut
)

from app.services.security import generate_api_key, hash_api_key
from app.services.rag import extract_text_from_file, chunk_text, generate_embedding, cosine_similarity, words
from app.services.executor import execute_agent_chat
from app.services.evaluator import evaluate_response
from app.services.prompt_optimizer import optimize_agent_prompt

router = APIRouter()

# --- Helper: Workspace Authorization ---
def verify_workspace_access(workspace_id: uuid.UUID, user: User, db: Session, required_role: str = "viewer") -> Workspace:
    ws = db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws.owner_id == user.id:
        return ws
    member = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id
        )
    )
    if not member:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    return ws

def record_audit(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID | None, action: str, r_type: str, r_id: str, details: dict = None):
    log = AuditLog(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        resource_type=r_type,
        resource_id=str(r_id),
        details_json=details or {}
    )
    db.add(log)

# ==============================================================================
# 1. AUTH & WORKSPACE
# ==============================================================================

@router.post("/auth/register", response_model=TokenOut, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == data.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        password_hash=hash_password(data.password)
    )
    db.add(user)
    db.flush()

    ws = Workspace(name=f"{data.full_name}'s Workspace", owner_id=user.id)
    db.add(ws)
    db.flush()

    # Pre-seed a default starter agent
    starter = Agent(
        workspace_id=ws.id,
        name="Support Strategist",
        description="Handles customer inquiries with grounded accuracy and editorial clarity.",
        category="support",
        system_prompt="You are Support Strategist, an authoritative and helpful AI support copilot. Answer inquiries directly, cite knowledge sources accurately, and adhere to strict editorial conciseness.",
        personality="Direct, professional, grounded",
        restrictions="Never fabricate company policies or release unconfirmed timeline commitments.",
        status="active"
    )
    db.add(starter)
    db.commit()
    db.refresh(user)

    record_audit(db, ws.id, user.id, "register", "user", str(user.id), {"email": user.email})
    db.commit()

    return TokenOut(access_token=create_access_token(str(user.id)), user=user)

@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenOut(access_token=create_access_token(str(user.id)), user=user)

@router.post("/auth/reset-password")
def reset_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user:
        # Avoid leaking email existence
        return {"status": "ok", "message": "Password reset processed if user exists."}
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"status": "ok", "message": "Password updated successfully"}

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user

@router.get("/workspaces", response_model=list[WorkspaceOut])
def list_workspaces(user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned = list(db.scalars(select(Workspace).where(Workspace.owner_id == user.id)))
    member_workspaces = list(db.scalars(
        select(Workspace).join(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
    ))
    all_ws = {w.id: w for w in (owned + member_workspaces)}
    return list(all_ws.values())

@router.post("/workspaces", response_model=WorkspaceOut, status_code=201)
def create_workspace(data: WorkspaceCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ws = Workspace(name=data.name, owner_id=user.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    record_audit(db, ws.id, user.id, "create_workspace", "workspace", str(ws.id))
    db.commit()
    return ws

@router.get("/workspaces/{workspace_id}/members", response_model=list[WorkspaceMemberOut])
def list_members(workspace_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    return list(db.scalars(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)))

@router.post("/workspaces/{workspace_id}/members", response_model=WorkspaceMemberOut, status_code=201)
def add_member(workspace_id: uuid.UUID, data: WorkspaceMemberAdd, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ws = verify_workspace_access(workspace_id, user, db, required_role="admin")
    target_user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not target_user:
        raise HTTPException(status_code=404, detail="User with this email not found")
    
    existing = db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == target_user.id))
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")
        
    member = WorkspaceMember(workspace_id=workspace_id, user_id=target_user.id, role=data.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    record_audit(db, workspace_id, user.id, "add_member", "workspace_member", str(member.id))
    db.commit()
    return member

# ==============================================================================
# 2. AGENTS & VERSIONING
# ==============================================================================

@router.get("/workspaces/{workspace_id}/agents", response_model=list[AgentOut])
def list_agents(workspace_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agents = list(db.scalars(select(Agent).where(Agent.workspace_id == workspace_id).order_by(Agent.created_at.desc())))
    for a in agents:
        a.knowledge_base_ids = [l.knowledge_base_id for l in a.knowledge_base_links]
    return agents

@router.get("/workspaces/{workspace_id}/agents/{agent_id}", response_model=AgentOut)
def get_agent(workspace_id: uuid.UUID, agent_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent = db.scalar(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.knowledge_base_ids = [l.knowledge_base_id for l in agent.knowledge_base_links]
    return agent

@router.post("/workspaces/{workspace_id}/agents", response_model=AgentOut, status_code=201)
def create_agent(workspace_id: uuid.UUID, data: AgentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent_data = data.model_dump(exclude={"knowledge_base_ids"})
    agent = Agent(workspace_id=workspace_id, **agent_data, current_version=1)
    db.add(agent)
    db.flush()

    # Link knowledge bases
    for kb_id in data.knowledge_base_ids:
        db.add(AgentKnowledgeBase(agent_id=agent.id, knowledge_base_id=kb_id))

    # Create Initial Version (v1)
    v1 = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        configuration_snapshot=agent_data,
        change_summary="Initial agent creation",
        is_published=True,
        created_by_id=user.id
    )
    db.add(v1)
    db.commit()
    db.refresh(agent)
    agent.knowledge_base_ids = data.knowledge_base_ids

    record_audit(db, workspace_id, user.id, "create_agent", "agent", str(agent.id), {"name": agent.name})
    db.commit()
    return agent

@router.patch("/workspaces/{workspace_id}/agents/{agent_id}", response_model=AgentOut)
def update_agent(workspace_id: uuid.UUID, agent_id: uuid.UUID, data: AgentUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent = db.scalar(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    update_dict = data.model_dump(exclude_unset=True)
    kb_ids = update_dict.pop("knowledge_base_ids", None)
    
    for k, v in update_dict.items():
        setattr(agent, k, v)
        
    if kb_ids is not None:
        db.query(AgentKnowledgeBase).filter(AgentKnowledgeBase.agent_id == agent.id).delete()
        for kb_id in kb_ids:
            db.add(AgentKnowledgeBase(agent_id=agent.id, knowledge_base_id=kb_id))

    db.commit()
    db.refresh(agent)
    agent.knowledge_base_ids = [l.knowledge_base_id for l in agent.knowledge_base_links]
    return agent

@router.post("/workspaces/{workspace_id}/agents/{agent_id}/publish", response_model=AgentVersionOut)
def publish_agent_version(workspace_id: uuid.UUID, agent_id: uuid.UUID, data: PublishVersionRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent = db.scalar(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    new_version_num = agent.current_version + 1
    agent.current_version = new_version_num
    agent.status = "active"

    snapshot = {
        "name": agent.name,
        "description": agent.description,
        "category": agent.category,
        "model": agent.model,
        "provider": agent.provider,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "system_prompt": agent.system_prompt,
        "role_description": agent.role_description,
        "personality": agent.personality,
        "restrictions": agent.restrictions,
        "response_format": agent.response_format,
        "tools_config": agent.tools_config,
    }

    version = AgentVersion(
        agent_id=agent.id,
        version_number=new_version_num,
        configuration_snapshot=snapshot,
        change_summary=data.change_summary,
        is_published=True,
        created_by_id=user.id
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    record_audit(db, workspace_id, user.id, "publish_version", "agent_version", str(version.id), {"version": new_version_num})
    db.commit()
    return version

@router.post("/workspaces/{workspace_id}/agents/{agent_id}/duplicate", response_model=AgentOut)
def duplicate_agent(workspace_id: uuid.UUID, agent_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    orig = db.scalar(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == workspace_id))
    if not orig:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    dup = Agent(
        workspace_id=workspace_id,
        name=f"{orig.name} (Copy)",
        description=orig.description,
        category=orig.category,
        avatar=orig.avatar,
        model=orig.model,
        provider=orig.provider,
        temperature=orig.temperature,
        max_tokens=orig.max_tokens,
        timeout_seconds=orig.timeout_seconds,
        status="draft",
        system_prompt=orig.system_prompt,
        role_description=orig.role_description,
        personality=orig.personality,
        restrictions=orig.restrictions,
        response_format=orig.response_format,
        tools_config=orig.tools_config,
        current_version=1
    )
    db.add(dup)
    db.flush()

    for l in orig.knowledge_base_links:
        db.add(AgentKnowledgeBase(agent_id=dup.id, knowledge_base_id=l.knowledge_base_id))

    db.add(AgentVersion(
        agent_id=dup.id,
        version_number=1,
        configuration_snapshot={"name": dup.name, "system_prompt": dup.system_prompt},
        change_summary="Duplicated from " + orig.name,
        is_published=False,
        created_by_id=user.id
    ))
    db.commit()
    db.refresh(dup)
    dup.knowledge_base_ids = [l.knowledge_base_id for l in dup.knowledge_base_links]
    return dup

@router.delete("/workspaces/{workspace_id}/agents/{agent_id}", status_code=204)
def delete_agent(workspace_id: uuid.UUID, agent_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent = db.scalar(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db.delete(agent)
    record_audit(db, workspace_id, user.id, "delete_agent", "agent", str(agent_id))
    db.commit()

# ==============================================================================
# 3. KNOWLEDGE BASE & RAG
# ==============================================================================

@router.get("/workspaces/{workspace_id}/knowledge-bases", response_model=list[KnowledgeBaseOut])
def list_knowledge_bases(workspace_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    return list(db.scalars(select(KnowledgeBase).where(KnowledgeBase.workspace_id == workspace_id).order_by(KnowledgeBase.created_at.desc())))

@router.post("/workspaces/{workspace_id}/knowledge-bases", response_model=KnowledgeBaseOut, status_code=201)
def create_knowledge_base(workspace_id: uuid.UUID, data: KnowledgeBaseCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    kb = KnowledgeBase(workspace_id=workspace_id, name=data.name, description=data.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    record_audit(db, workspace_id, user.id, "create_knowledge_base", "knowledge_base", str(kb.id))
    db.commit()
    return kb

@router.delete("/workspaces/{workspace_id}/knowledge-bases/{kb_id}", status_code=204)
def delete_knowledge_base(workspace_id: uuid.UUID, kb_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    kb = db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.workspace_id == workspace_id))
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    db.delete(kb)
    db.commit()

@router.post("/workspaces/{workspace_id}/knowledge-bases/{kb_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    workspace_id: uuid.UUID,
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    verify_workspace_access(workspace_id, user, db)
    kb = db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.workspace_id == workspace_id))
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
        
    content_bytes = await file.read()
    raw_text = extract_text_from_file(file.filename, content_bytes)
    
    chunks = chunk_text(raw_text)
    
    doc = Document(
        knowledge_base_id=kb.id,
        name=file.filename,
        file_type=file.filename.split(".")[-1].lower(),
        file_size=len(content_bytes),
        status="ready",
        raw_text=raw_text,
        chunk_count=len(chunks)
    )
    db.add(doc)
    db.flush()

    for idx, c in enumerate(chunks):
        emb = generate_embedding(c)
        db.add(DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=c,
            metadata_json={"doc_name": file.filename, "chunk_index": idx, "length": len(c)},
            embedding_json=emb
        ))

    db.commit()
    db.refresh(doc)
    record_audit(db, workspace_id, user.id, "upload_document", "document", str(doc.id), {"filename": file.filename})
    db.commit()
    return doc

@router.get("/workspaces/{workspace_id}/documents/{doc_id}", response_model=DocumentOut)
def get_document_details(workspace_id: uuid.UUID, doc_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    doc = db.scalar(select(Document).join(KnowledgeBase).where(Document.id == doc_id, KnowledgeBase.workspace_id == workspace_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/workspaces/{workspace_id}/documents/{doc_id}", status_code=204)
def delete_document(workspace_id: uuid.UUID, doc_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    doc = db.scalar(select(Document).join(KnowledgeBase).where(Document.id == doc_id, KnowledgeBase.workspace_id == workspace_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()

@router.post("/workspaces/{workspace_id}/knowledge-bases/{kb_id}/retrieve", response_model=RetrievalResponse)
def retrieve_knowledge(
    workspace_id: uuid.UUID,
    kb_id: uuid.UUID,
    query: RetrievalQuery,
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    verify_workspace_access(workspace_id, user, db)
    q_emb = generate_embedding(query.query)
    
    chunks = db.query(DocumentChunk, Document.name).join(Document).filter(Document.knowledge_base_id == kb_id).all()
    
    scored = []
    for c, doc_name in chunks:
        sim = cosine_similarity(q_emb, c.embedding_json or [])
        # Keyword boost
        q_words = words(query.query)
        c_words = words(c.content)
        overlap = len(q_words & c_words) / max(1, len(q_words))
        composite = (sim * 0.5) + (overlap * 0.5)
        
        if composite >= query.threshold:
            scored.append({
                "chunk_id": str(c.id),
                "document_id": str(c.document_id),
                "document_name": doc_name,
                "chunk_index": c.chunk_index,
                "score": round(composite, 3),
                "content": c.content
            })
            
    scored.sort(key=lambda x: x["score"], reverse=True)
    results = scored[:query.top_k]
    
    return RetrievalResponse(
        query=query.query,
        total_found=len(results),
        chunks=[RetrievalChunkOut(**r) for r in results]
    )

# ==============================================================================
# 4. CHAT, PLAYGROUND & EXECUTION
# ==============================================================================

@router.get("/workspaces/{workspace_id}/agents/{agent_id}/conversations", response_model=list[ConversationOut])
def list_conversations(workspace_id: uuid.UUID, agent_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    return list(db.scalars(
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id, Conversation.agent_id == agent_id)
        .order_by(Conversation.updated_at.desc())
    ))

@router.post("/workspaces/{workspace_id}/agents/{agent_id}/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(workspace_id: uuid.UUID, agent_id: uuid.UUID, data: ConversationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent = db.scalar(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    conv = Conversation(workspace_id=workspace_id, agent_id=agent_id, title=data.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv

@router.get("/workspaces/{workspace_id}/conversations/{conv_id}", response_model=ConversationOut)
def get_conversation(workspace_id: uuid.UUID, conv_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    conv = db.scalar(select(Conversation).where(Conversation.id == conv_id, Conversation.workspace_id == workspace_id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@router.delete("/workspaces/{workspace_id}/conversations/{conv_id}", status_code=204)
def delete_conversation(workspace_id: uuid.UUID, conv_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    conv = db.scalar(select(Conversation).where(Conversation.id == conv_id, Conversation.workspace_id == workspace_id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()

@router.post("/workspaces/{workspace_id}/conversations/{conv_id}/messages", response_model=MessageOut)
def send_message(workspace_id: uuid.UUID, conv_id: uuid.UUID, data: ChatMessageInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    conv = db.scalar(select(Conversation).where(Conversation.id == conv_id, Conversation.workspace_id == workspace_id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    agent = conv.agent

    # 1. Store user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=data.content
    )
    db.add(user_msg)
    db.flush()

    # 2. Gather knowledge chunks from linked knowledge bases
    kb_links = list(agent.knowledge_base_links)
    rag_chunks = []
    if kb_links:
        kb_ids = [l.knowledge_base_id for l in kb_links]
        q_emb = generate_embedding(data.content)
        candidate_chunks = db.query(DocumentChunk, Document.name).join(Document).filter(Document.knowledge_base_id.in_(kb_ids)).all()
        scored = []
        for c, doc_name in candidate_chunks:
            sim = cosine_similarity(q_emb, c.embedding_json or [])
            q_words = words(data.content)
            c_words = words(c.content)
            overlap = len(q_words & c_words) / max(1, len(q_words))
            composite = (sim * 0.4) + (overlap * 0.6)
            if composite > 0.08:
                scored.append({
                    "document_name": doc_name,
                    "chunk_index": c.chunk_index,
                    "score": composite,
                    "content": c.content
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        rag_chunks = scored[:4]

    # 3. Execute Agent
    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    result = execute_agent_chat(agent, history, data.content, rag_chunks)

    # 4. Store Assistant response
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=result["reply"],
        citations_json=result["citations"],
        token_count=result["tokens"],
        latency_ms=result["latency_ms"],
        cost_est=result["cost_est"],
        debug_json=result["debug"]
    )
    db.add(assistant_msg)

    # Record usage event
    db.add(UsageEvent(
        workspace_id=workspace_id,
        agent_id=agent.id,
        event_type="chat",
        tokens=result["tokens"],
        latency_ms=result["latency_ms"],
        cost=result["cost_est"],
        metadata_json={"conversation_id": str(conv.id)}
    ))

    # Auto-title conversation if default
    if conv.title == "New Conversation":
        snippet = data.content[:35].strip()
        conv.title = f"{snippet}..." if len(data.content) > 35 else snippet

    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg

# ==============================================================================
# 5. DATASETS & TRAINING STUDIO
# ==============================================================================

@router.get("/workspaces/{workspace_id}/datasets", response_model=list[DatasetOut])
def list_datasets(workspace_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    return list(db.scalars(select(Dataset).where(Dataset.workspace_id == workspace_id).order_by(Dataset.created_at.desc())))

@router.post("/workspaces/{workspace_id}/datasets", response_model=DatasetOut, status_code=201)
def create_dataset(workspace_id: uuid.UUID, data: DatasetCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    ds = Dataset(workspace_id=workspace_id, name=data.name, description=data.description)
    db.add(ds)
    db.commit()
    db.refresh(ds)
    record_audit(db, workspace_id, user.id, "create_dataset", "dataset", str(ds.id))
    db.commit()
    return ds

@router.delete("/workspaces/{workspace_id}/datasets/{dataset_id}", status_code=204)
def delete_dataset(workspace_id: uuid.UUID, dataset_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    ds = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.workspace_id == workspace_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(ds)
    db.commit()

@router.post("/workspaces/{workspace_id}/datasets/{dataset_id}/examples", response_model=DatasetExampleOut, status_code=201)
def add_dataset_example(workspace_id: uuid.UUID, dataset_id: uuid.UUID, data: DatasetExampleCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    ds = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.workspace_id == workspace_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    ex = DatasetExample(dataset_id=dataset_id, **data.model_dump())
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex

@router.delete("/workspaces/{workspace_id}/datasets/{dataset_id}/examples/{example_id}", status_code=204)
def delete_dataset_example(workspace_id: uuid.UUID, dataset_id: uuid.UUID, example_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    ex = db.scalar(select(DatasetExample).where(DatasetExample.id == example_id, DatasetExample.dataset_id == dataset_id))
    if not ex:
        raise HTTPException(status_code=404, detail="Example not found")
    db.delete(ex)
    db.commit()

@router.post("/workspaces/{workspace_id}/datasets/{dataset_id}/generate-synthetic")
def generate_synthetic_examples(workspace_id: uuid.UUID, dataset_id: uuid.UUID, data: SyntheticExampleGenerateRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    ds = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.workspace_id == workspace_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    docs = list(db.scalars(select(Document).where(Document.knowledge_base_id == data.knowledge_base_id)))
    if not docs:
        raise HTTPException(status_code=400, detail="Selected knowledge base has no documents")

    generated = []
    for doc in docs[:3]:
        chunks = doc.chunks[:data.count]
        for c in chunks:
            # Generate synthetic question and answer pair from chunk content
            first_sentence = c.content.split(". ")[0].strip()
            q = f"What details are specified regarding '{first_sentence[:45]}'?"
            ans = f"{c.content[:240]}..."
            ex = DatasetExample(
                dataset_id=ds.id,
                question=q,
                expected_answer=ans,
                reference_context=c.content,
                category=data.category
            )
            db.add(ex)
            generated.append(q)

    db.commit()
    record_audit(db, workspace_id, user.id, "generate_synthetic_examples", "dataset", str(ds.id), {"count": len(generated)})
    db.commit()
    return {"status": "ok", "generated_count": len(generated)}

# ==============================================================================
# 6. EVALUATION ENGINE
# ==============================================================================

@router.post("/workspaces/{workspace_id}/evaluations", response_model=EvaluationOut)
def evaluate_single_response(workspace_id: uuid.UUID, data: EvaluationRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent = db.scalar(select(Agent).where(Agent.id == data.agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    res = evaluate_response(
        question=data.question,
        expected_answer=data.expected_answer,
        actual_answer=data.actual_answer,
        system_prompt=agent.system_prompt
    )

    # Persist as a single-evaluation run
    run = EvaluationRun(
        workspace_id=workspace_id,
        agent_id=agent.id,
        agent_version=agent.current_version,
        status="completed",
        overall_score=res["overall_score"],
        grade=res["grade"],
        summary_json=res
    )
    db.add(run)
    db.flush()

    db.add(EvaluationResult(
        run_id=run.id,
        question=data.question,
        expected_answer=data.expected_answer,
        actual_answer=data.actual_answer,
        accuracy=res["accuracy"]["score"],
        relevance=res["relevance"]["score"],
        completeness=res["completeness"]["score"],
        instruction_following=res["instruction_following"]["score"],
        hallucination_risk=res["hallucination_risk"]["score"],
        safety=res["safety"]["score"],
        score=res["overall_score"],
        feedback=res["feedback"],
        suggestions_json=res["suggestions"]
    ))

    db.add(UsageEvent(
        workspace_id=workspace_id,
        agent_id=agent.id,
        event_type="eval",
        tokens=150,
        latency_ms=18.0,
        cost=0.0001,
        metadata_json={"score": res["overall_score"]}
    ))

    db.commit()
    return EvaluationOut(agent_id=agent.id, **res)

@router.post("/workspaces/{workspace_id}/evaluations/batch", response_model=EvaluationRunOut)
def run_batch_evaluation(workspace_id: uuid.UUID, data: BatchEvaluationRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent = db.scalar(select(Agent).where(Agent.id == data.agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    dataset = db.scalar(select(Dataset).where(Dataset.id == data.dataset_id, Dataset.workspace_id == workspace_id))
    if not dataset or not dataset.examples:
        raise HTTPException(status_code=400, detail="Dataset not found or contains no test examples")

    run = EvaluationRun(
        workspace_id=workspace_id,
        agent_id=agent.id,
        agent_version=agent.current_version,
        dataset_id=dataset.id,
        status="running"
    )
    db.add(run)
    db.flush()

    scores = []
    results = []
    for ex in dataset.examples:
        # Run agent chat execution
        exec_out = execute_agent_chat(agent, [], ex.question, [])
        eval_out = evaluate_response(
            question=ex.question,
            expected_answer=ex.expected_answer,
            actual_answer=exec_out["reply"],
            system_prompt=agent.system_prompt,
            reference_context=ex.reference_context
        )
        scores.append(eval_out["overall_score"])

        res_item = EvaluationResult(
            run_id=run.id,
            example_id=ex.id,
            question=ex.question,
            expected_answer=ex.expected_answer,
            actual_answer=exec_out["reply"],
            accuracy=eval_out["accuracy"]["score"],
            relevance=eval_out["relevance"]["score"],
            completeness=eval_out["completeness"]["score"],
            instruction_following=eval_out["instruction_following"]["score"],
            hallucination_risk=eval_out["hallucination_risk"]["score"],
            safety=eval_out["safety"]["score"],
            score=eval_out["overall_score"],
            feedback=eval_out["feedback"],
            suggestions_json=eval_out["suggestions"]
        )
        db.add(res_item)
        results.append(res_item)

    avg_score = round(sum(scores) / max(1, len(scores)), 1)
    run.overall_score = avg_score
    run.grade = "Superior" if avg_score >= 88 else "Strong" if avg_score >= 75 else "Needs improvement" if avg_score >= 55 else "Failing"
    run.status = "completed"
    run.summary_json = {
        "example_count": len(dataset.examples),
        "avg_score": avg_score,
        "grade": run.grade,
        "dataset_name": dataset.name
    }

    db.add(UsageEvent(
        workspace_id=workspace_id,
        agent_id=agent.id,
        event_type="eval",
        tokens=len(dataset.examples) * 200,
        latency_ms=len(dataset.examples) * 35.0,
        cost=len(dataset.examples) * 0.0003,
        metadata_json={"batch_run_id": str(run.id), "avg_score": avg_score}
    ))

    db.commit()
    db.refresh(run)
    record_audit(db, workspace_id, user.id, "run_batch_evaluation", "evaluation_run", str(run.id), {"score": avg_score})
    db.commit()
    return run

@router.get("/workspaces/{workspace_id}/evaluations/runs", response_model=list[EvaluationRunOut])
def list_evaluation_runs(workspace_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    return list(db.scalars(
        select(EvaluationRun)
        .where(EvaluationRun.workspace_id == workspace_id)
        .order_by(EvaluationRun.created_at.desc())
    ))

# ==============================================================================
# 7. PROMPT OPTIMIZER
# ==============================================================================

@router.post("/workspaces/{workspace_id}/prompt-optimizer/generate", response_model=PromptOptimizationOut)
def generate_prompt_optimization(workspace_id: uuid.UUID, data: PromptOptimizeRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent = db.scalar(select(Agent).where(Agent.id == data.agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    opt = optimize_agent_prompt(
        original_prompt=agent.system_prompt,
        agent_name=agent.name,
        focus_areas=data.focus_areas
    )

    record = PromptOptimization(
        workspace_id=workspace_id,
        agent_id=agent.id,
        original_prompt=opt["original_prompt"],
        proposed_prompt=opt["proposed_prompt"],
        rationale=opt["rationale"],
        diff_json=opt["diff_json"],
        status="pending",
        score_delta=opt["score_delta"]
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.post("/workspaces/{workspace_id}/prompt-optimizer/{opt_id}/approve")
def approve_prompt_optimization(workspace_id: uuid.UUID, opt_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    opt = db.scalar(select(PromptOptimization).where(PromptOptimization.id == opt_id, PromptOptimization.workspace_id == workspace_id))
    if not opt:
        raise HTTPException(status_code=404, detail="Optimization record not found")
        
    agent = db.scalar(select(Agent).where(Agent.id == opt.agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Update agent system prompt & create new version
    agent.system_prompt = opt.proposed_prompt
    agent.current_version += 1
    opt.status = "approved"

    v = AgentVersion(
        agent_id=agent.id,
        version_number=agent.current_version,
        configuration_snapshot={"name": agent.name, "system_prompt": agent.system_prompt},
        change_summary=f"Applied Prompt Optimizer recommendations (+{opt.score_delta}% est.)",
        is_published=True,
        created_by_id=user.id
    )
    db.add(v)
    db.commit()
    record_audit(db, workspace_id, user.id, "approve_prompt_opt", "agent", str(agent.id), {"version": agent.current_version})
    db.commit()
    return {"status": "ok", "message": "Prompt optimization applied and new agent version published."}

# ==============================================================================
# 8. DEPLOYMENTS & API KEYS
# ==============================================================================

@router.get("/workspaces/{workspace_id}/deployments", response_model=list[DeploymentOut])
def list_deployments(workspace_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    return list(db.scalars(select(Deployment).where(Deployment.workspace_id == workspace_id).order_by(Deployment.created_at.desc())))

@router.post("/workspaces/{workspace_id}/deployments", response_model=DeploymentOut, status_code=201)
def create_deployment(workspace_id: uuid.UUID, data: DeploymentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    agent = db.scalar(select(Agent).where(Agent.id == data.agent_id, Agent.workspace_id == workspace_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    dep = Deployment(
        workspace_id=workspace_id,
        agent_id=agent.id,
        name=data.name,
        environment=data.environment,
        rate_limit_rpm=data.rate_limit_rpm,
        widget_config=data.widget_config or {
            "title": agent.name,
            "welcome_message": f"Hello! How can I assist you with {agent.category}?",
            "primary_color": "#0A0A0A",
            "accent_color": "#EF4444"
        }
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    record_audit(db, workspace_id, user.id, "create_deployment", "deployment", str(dep.id))
    db.commit()
    return dep

@router.patch("/workspaces/{workspace_id}/deployments/{dep_id}", response_model=DeploymentOut)
def update_deployment(workspace_id: uuid.UUID, dep_id: uuid.UUID, data: DeploymentUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    dep = db.scalar(select(Deployment).where(Deployment.id == dep_id, Deployment.workspace_id == workspace_id))
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
        
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(dep, k, v)
        
    db.commit()
    db.refresh(dep)
    return dep

@router.delete("/workspaces/{workspace_id}/deployments/{dep_id}", status_code=204)
def delete_deployment(workspace_id: uuid.UUID, dep_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    dep = db.scalar(select(Deployment).where(Deployment.id == dep_id, Deployment.workspace_id == workspace_id))
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    db.delete(dep)
    db.commit()

@router.get("/workspaces/{workspace_id}/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(workspace_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    return list(db.scalars(select(ApiKey).where(ApiKey.workspace_id == workspace_id).order_by(ApiKey.created_at.desc())))

@router.post("/workspaces/{workspace_id}/api-keys", response_model=ApiKeyCreatedOut, status_code=201)
def create_api_key(workspace_id: uuid.UUID, data: ApiKeyCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    raw_key, key_hash, prefix = generate_api_key()
    
    key_obj = ApiKey(
        workspace_id=workspace_id,
        deployment_id=data.deployment_id,
        name=data.name,
        key_hash=key_hash,
        prefix=prefix,
        scopes=data.scopes
    )
    db.add(key_obj)
    db.commit()
    db.refresh(key_obj)

    record_audit(db, workspace_id, user.id, "create_api_key", "api_key", str(key_obj.id), {"prefix": prefix})
    db.commit()

    return ApiKeyCreatedOut(
        id=key_obj.id,
        workspace_id=key_obj.workspace_id,
        deployment_id=key_obj.deployment_id,
        name=key_obj.name,
        prefix=key_obj.prefix,
        is_active=key_obj.is_active,
        scopes=key_obj.scopes,
        created_at=key_obj.created_at,
        expires_at=key_obj.expires_at,
        last_used_at=key_obj.last_used_at,
        raw_key=raw_key
    )

@router.delete("/workspaces/{workspace_id}/api-keys/{key_id}", status_code=204)
def revoke_api_key(workspace_id: uuid.UUID, key_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    k = db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.workspace_id == workspace_id))
    if not k:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(k)
    record_audit(db, workspace_id, user.id, "revoke_api_key", "api_key", str(key_id))
    db.commit()

# --- Public API Endpoint for Embed / External Clients ---
@router.post("/public/deployments/{dep_id}/chat", response_model=PublicChatResponse)
def public_agent_chat(
    dep_id: uuid.UUID,
    data: PublicChatRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Bearer API key header")
    raw_key = authorization.split("Bearer ")[1].strip()
    k_hash = hash_api_key(raw_key)

    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == k_hash, ApiKey.is_active == True))
    if not api_key:
        raise HTTPException(status_code=401, detail="Unauthorized API key")

    dep = db.scalar(select(Deployment).where(Deployment.id == dep_id, Deployment.status == "active"))
    if not dep:
        raise HTTPException(status_code=404, detail="Active deployment not found")

    api_key.last_used_at = datetime.now(timezone.utc)
    dep.total_requests += 1

    agent = dep.agent
    rag_chunks = []
    for l in agent.knowledge_base_links:
        q_emb = generate_embedding(data.message)
        chunks = db.query(DocumentChunk, Document.name).join(Document).filter(Document.knowledge_base_id == l.knowledge_base_id).all()
        for c, doc_name in chunks:
            sim = cosine_similarity(q_emb, c.embedding_json or [])
            if sim > 0.1:
                rag_chunks.append({"document_name": doc_name, "chunk_index": c.chunk_index, "score": sim, "content": c.content})

    exec_result = execute_agent_chat(agent, [], data.message, rag_chunks[:3])

    db.add(UsageEvent(
        workspace_id=dep.workspace_id,
        agent_id=agent.id,
        deployment_id=dep.id,
        event_type="api_request",
        tokens=exec_result["tokens"],
        latency_ms=exec_result["latency_ms"],
        cost=exec_result["cost_est"]
    ))
    db.commit()

    return PublicChatResponse(
        reply=exec_result["reply"],
        citations=exec_result["citations"],
        tokens=exec_result["tokens"],
        latency_ms=exec_result["latency_ms"]
    )

# ==============================================================================
# 9. ANALYTICS & AUDIT LOGS
# ==============================================================================

@router.get("/workspaces/{workspace_id}/analytics", response_model=UsageMetricsOut)
def get_analytics(workspace_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)

    total_convs = db.scalar(select(func.count(Conversation.id)).where(Conversation.workspace_id == workspace_id)) or 0
    total_messages = db.scalar(select(func.count(Message.id)).join(Conversation).where(Conversation.workspace_id == workspace_id)) or 0
    
    usage_stats = db.query(
        func.sum(UsageEvent.tokens),
        func.avg(UsageEvent.latency_ms),
        func.sum(UsageEvent.cost),
        func.count(UsageEvent.id)
    ).filter(UsageEvent.workspace_id == workspace_id).first()

    total_tokens = int(usage_stats[0] or 0)
    avg_latency = round(float(usage_stats[1] or 0.0), 1)
    total_cost = round(float(usage_stats[2] or 0.0), 4)

    eval_stats = db.query(
        func.count(EvaluationRun.id),
        func.avg(EvaluationRun.overall_score)
    ).filter(EvaluationRun.workspace_id == workspace_id).first()

    eval_count = int(eval_stats[0] or 0)
    avg_eval_score = round(float(eval_stats[1] or 0.0), 1)

    # Agent usage distribution
    agents = db.scalars(select(Agent).where(Agent.workspace_id == workspace_id)).all()
    agent_distribution = []
    for a in agents:
        tok_sum = db.scalar(select(func.sum(UsageEvent.tokens)).where(UsageEvent.agent_id == a.id)) or 0
        agent_distribution.append({
            "agent_id": str(a.id),
            "name": a.name,
            "tokens": int(tok_sum),
            "status": a.status
        })

    # Daily dummy/calculated telemetry points for charts
    daily_stats = [
        {"day": "Mon", "tokens": max(50, int(total_tokens * 0.15)), "latency": 45, "cost": 0.02},
        {"day": "Tue", "tokens": max(70, int(total_tokens * 0.22)), "latency": 52, "cost": 0.03},
        {"day": "Wed", "tokens": max(120, int(total_tokens * 0.35)), "latency": 48, "cost": 0.05},
        {"day": "Thu", "tokens": max(90, int(total_tokens * 0.18)), "latency": 46, "cost": 0.02},
        {"day": "Fri", "tokens": max(40, int(total_tokens * 0.10)), "latency": 44, "cost": 0.01},
    ]

    return UsageMetricsOut(
        total_conversations=total_convs,
        total_messages=total_messages,
        total_tokens=total_tokens,
        avg_latency_ms=avg_latency,
        total_estimated_cost=total_cost,
        evaluations_count=eval_count,
        avg_evaluation_score=avg_eval_score,
        daily_stats=daily_stats,
        agent_distribution=agent_distribution
    )

@router.get("/workspaces/{workspace_id}/audit-logs", response_model=list[AuditLogOut])
def get_audit_logs(workspace_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    verify_workspace_access(workspace_id, user, db)
    return list(db.scalars(
        select(AuditLog)
        .where(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    ))
