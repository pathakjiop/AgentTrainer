import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --- Auth & User ---
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str = "member"
    is_active: bool = True
    created_at: datetime

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class PasswordResetRequest(BaseModel):
    email: EmailStr
    new_password: str = Field(min_length=8)

# --- Workspaces ---
class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

class WorkspaceMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    created_at: datetime
    user: UserOut

class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime

class WorkspaceMemberAdd(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(owner|admin|member|viewer)$")

# --- Agents & Versions ---
class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    category: str = "general"
    avatar: str = ""
    model: str = "gpt-4o-mini"
    provider: str = "mock"
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=64, le=32000)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    system_prompt: str = Field(default="You are a helpful assistant.", min_length=1)
    role_description: str = ""
    personality: str = "Professional, concise, accurate"
    restrictions: str = ""
    response_format: str = "markdown"
    tools_config: dict = Field(default_factory=dict)
    knowledge_base_ids: list[uuid.UUID] = Field(default_factory=list)

class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    avatar: str | None = None
    model: str | None = None
    provider: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=64, le=32000)
    timeout_seconds: int | None = Field(default=None, ge=5, le=300)
    system_prompt: str | None = Field(default=None, min_length=1)
    role_description: str | None = None
    personality: str | None = None
    restrictions: str | None = None
    response_format: str | None = None
    tools_config: dict | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|paused|archived)$")
    knowledge_base_ids: list[uuid.UUID] | None = None

class AgentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_id: uuid.UUID
    version_number: int
    configuration_snapshot: dict
    change_summary: str
    is_published: bool
    created_at: datetime

class AgentOut(AgentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    versions: list[AgentVersionOut] = Field(default_factory=list)

class PublishVersionRequest(BaseModel):
    change_summary: str = Field(default="Published new release", max_length=500)

# --- Knowledge Base & RAG ---
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""

class DocumentChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    chunk_index: int
    content: str
    metadata_json: dict
    created_at: datetime

class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    name: str
    file_type: str
    file_size: int
    status: str
    error_message: str
    chunk_count: int
    created_at: datetime

class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentOut] = Field(default_factory=list)

class RetrievalQuery(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=20)
    threshold: float = Field(default=0.15, ge=0.0, le=1.0)

class RetrievalChunkOut(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    chunk_index: int
    score: float
    content: str

class RetrievalResponse(BaseModel):
    query: str
    total_found: int
    chunks: list[RetrievalChunkOut]

# --- Chat & Playground ---
class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations_json: list
    token_count: int
    latency_ms: float
    cost_est: float
    debug_json: dict
    created_at: datetime

class ConversationCreate(BaseModel):
    agent_id: uuid.UUID | None = None
    title: str = "New Conversation"

class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = Field(default_factory=list)

class ChatMessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=20000)

class ChatExecutionResult(BaseModel):
    message: MessageOut
    citations: list[dict]
    debug: dict

# --- Datasets & Training Studio ---
class DatasetExampleCreate(BaseModel):
    question: str = Field(min_length=1)
    expected_answer: str = Field(min_length=1)
    reference_context: str = ""
    category: str = "general"
    metadata_json: dict = Field(default_factory=dict)

class DatasetExampleOut(DatasetExampleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    dataset_id: uuid.UUID
    created_at: datetime

class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""

class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    examples: list[DatasetExampleOut] = Field(default_factory=list)

class SyntheticExampleGenerateRequest(BaseModel):
    knowledge_base_id: uuid.UUID
    count: int = Field(default=5, ge=1, le=25)
    category: str = "synthetic"

# --- Evaluation Engine ---
class EvaluationDimension(BaseModel):
    score: float
    feedback: str

class EvaluationRequest(BaseModel):
    agent_id: uuid.UUID
    question: str = Field(min_length=1, max_length=10000)
    expected_answer: str = Field(min_length=1, max_length=20000)
    actual_answer: str = Field(min_length=1, max_length=20000)

class EvaluationOut(BaseModel):
    agent_id: uuid.UUID
    overall_score: float
    grade: str
    accuracy: EvaluationDimension
    relevance: EvaluationDimension
    completeness: EvaluationDimension
    instruction_following: EvaluationDimension
    hallucination_risk: EvaluationDimension
    safety: EvaluationDimension
    suggestions: list[str]

class BatchEvaluationRequest(BaseModel):
    agent_id: uuid.UUID
    dataset_id: uuid.UUID

class EvaluationResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    question: str
    expected_answer: str
    actual_answer: str
    accuracy: float
    relevance: float
    completeness: float
    instruction_following: float
    hallucination_risk: float
    safety: float
    score: float
    feedback: str
    suggestions_json: list
    created_at: datetime

class EvaluationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID
    agent_version: int
    dataset_id: uuid.UUID | None
    status: str
    overall_score: float
    grade: str
    summary_json: dict
    created_at: datetime
    results: list[EvaluationResultOut] = Field(default_factory=list)

# --- Prompt Optimizer ---
class PromptOptimizeRequest(BaseModel):
    agent_id: uuid.UUID
    focus_areas: list[str] = Field(default_factory=list)

class PromptOptimizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID
    original_prompt: str
    proposed_prompt: str
    rationale: str
    diff_json: dict
    status: str
    score_delta: float
    created_at: datetime

# --- Deployments & API Keys ---
class DeploymentCreate(BaseModel):
    agent_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    environment: str = "production"
    rate_limit_rpm: int = Field(default=60, ge=1, le=1000)
    widget_config: dict = Field(default_factory=dict)

class DeploymentUpdate(BaseModel):
    name: str | None = None
    status: str | None = Field(default=None, pattern="^(active|paused|archived)$")
    rate_limit_rpm: int | None = None
    widget_config: dict | None = None

class ApiKeyCreate(BaseModel):
    deployment_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=100)
    scopes: str = "chat:read,chat:write"
    expires_in_days: int | None = 365

class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    deployment_id: uuid.UUID | None
    name: str
    prefix: str
    is_active: bool
    scopes: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None

class ApiKeyCreatedOut(ApiKeyOut):
    raw_key: str

class DeploymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    environment: str
    status: str
    widget_config: dict
    rate_limit_rpm: int
    total_requests: int
    created_at: datetime
    updated_at: datetime
    api_keys: list[ApiKeyOut] = Field(default_factory=list)

class PublicChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    session_id: str | None = None

class PublicChatResponse(BaseModel):
    reply: str
    citations: list[dict] = Field(default_factory=list)
    tokens: int
    latency_ms: float

# --- Analytics & Audit Logs ---
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str
    details_json: dict
    created_at: datetime

class UsageMetricsOut(BaseModel):
    total_conversations: int
    total_messages: int
    total_tokens: int
    avg_latency_ms: float
    total_estimated_cost: float
    evaluations_count: int
    avg_evaluation_score: float
    daily_stats: list[dict]
    agent_distribution: list[dict]
