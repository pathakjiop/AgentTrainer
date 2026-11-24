import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_full_workflow():
    # 1. Register User
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Editorial Director",
        "password": "Password123!"
    })
    assert reg_res.status_code == 201
    auth_data = reg_res.json()
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Workspaces
    ws_res = client.get("/api/v1/workspaces", headers=headers)
    assert ws_res.status_code == 200
    workspaces = ws_res.json()
    assert len(workspaces) >= 1
    ws_id = workspaces[0]["id"]

    # 3. Create Agent
    agent_res = client.post(f"/api/v1/workspaces/{ws_id}/agents", headers=headers, json={
        "name": "Culture Critic",
        "description": "Bold cultural commentary with high editorial standards.",
        "category": "editorial",
        "system_prompt": "You are Culture Critic. Provide sharp, incisive commentary on modern culture and technology.",
        "personality": "Opinionated, erudite, razor-sharp",
        "restrictions": "Never use cliched marketing buzzwords.",
        "model": "gpt-4o-mini",
        "temperature": 0.3
    })
    assert agent_res.status_code == 201
    agent = agent_res.json()
    agent_id = agent["id"]
    assert agent["name"] == "Culture Critic"
    assert agent["current_version"] == 1

    # 4. Publish New Version
    pub_res = client.post(f"/api/v1/workspaces/{ws_id}/agents/{agent_id}/publish", headers=headers, json={
        "change_summary": "Version 2 release with reinforced editorial voice"
    })
    assert pub_res.status_code == 200
    assert pub_res.json()["version_number"] == 2

    # 5. Duplicate Agent
    dup_res = client.post(f"/api/v1/workspaces/{ws_id}/agents/{agent_id}/duplicate", headers=headers)
    assert dup_res.status_code == 200
    assert "Copy" in dup_res.json()["name"]

    # 6. Knowledge Base & Document Upload
    kb_res = client.post(f"/api/v1/workspaces/{ws_id}/knowledge-bases", headers=headers, json={
        "name": "Magazine Style Guide",
        "description": "VoiceBox typography, contrast, and layout specifications."
    })
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    doc_content = b"VoiceBox is a high-contrast editorial design system. Headings must use Archivo Black at 38px or larger. The accent color is #EF4444 and must be used with restraint."
    doc_res = client.post(
        f"/api/v1/workspaces/{ws_id}/knowledge-bases/{kb_id}/documents",
        headers=headers,
        files={"file": ("style_guide.txt", doc_content, "text/plain")}
    )
    assert doc_res.status_code == 201
    doc = doc_res.json()
    assert doc["chunk_count"] >= 1

    # 7. Semantic Retrieval
    ret_res = client.post(
        f"/api/v1/workspaces/{ws_id}/knowledge-bases/{kb_id}/retrieve",
        headers=headers,
        json={"query": "What font should headings use in VoiceBox?", "top_k": 2}
    )
    assert ret_res.status_code == 200
    ret_data = ret_res.json()
    assert ret_data["total_found"] >= 1
    assert "Archivo Black" in ret_data["chunks"][0]["content"]

    # 8. Link KB to Agent & Chat Execution
    client.patch(f"/api/v1/workspaces/{ws_id}/agents/{agent_id}", headers=headers, json={
        "knowledge_base_ids": [kb_id]
    })

    conv_res = client.post(f"/api/v1/workspaces/{ws_id}/agents/{agent_id}/conversations", headers=headers, json={
        "title": "Style Inquiry"
    })
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/workspaces/{ws_id}/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "What is the heading font and accent color specified in our style guide?"}
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["role"] == "assistant"
    assert len(msg_data["citations_json"]) >= 1
    assert msg_data["token_count"] > 0

    # 9. Training Studio: Dataset & Synthetic Generation
    ds_res = client.post(f"/api/v1/workspaces/{ws_id}/datasets", headers=headers, json={
        "name": "Design Q&A Eval Set",
        "description": "Validation cases for VoiceBox rules"
    })
    assert ds_res.status_code == 201
    ds_id = ds_res.json()["id"]

    ex_res = client.post(f"/api/v1/workspaces/{ws_id}/datasets/{ds_id}/examples", headers=headers, json={
        "question": "What font is used for headers in VoiceBox?",
        "expected_answer": "Archivo Black is used for display headlines at 38px or larger.",
        "category": "typography"
    })
    assert ex_res.status_code == 201

    # Synthetic generation from knowledge base
    gen_res = client.post(f"/api/v1/workspaces/{ws_id}/datasets/{ds_id}/generate-synthetic", headers=headers, json={
        "knowledge_base_id": kb_id,
        "count": 2
    })
    assert gen_res.status_code == 200

    # 10. Evaluation Engine: Single and Batch Evaluation
    eval_res = client.post(f"/api/v1/workspaces/{ws_id}/evaluations", headers=headers, json={
        "agent_id": agent_id,
        "question": "What is the accent color of VoiceBox?",
        "expected_answer": "The primary accent color is #EF4444 red, used sparingly for emphasis.",
        "actual_answer": "VoiceBox utilizes #EF4444 red as its sole editorial accent."
    })
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["overall_score"] > 60
    assert "accuracy" in eval_data

    # Batch eval against dataset
    batch_res = client.post(f"/api/v1/workspaces/{ws_id}/evaluations/batch", headers=headers, json={
        "agent_id": agent_id,
        "dataset_id": ds_id
    })
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert batch_data["status"] == "completed"
    assert batch_data["overall_score"] > 0

    # 11. Prompt Optimizer
    opt_res = client.post(f"/api/v1/workspaces/{ws_id}/prompt-optimizer/generate", headers=headers, json={
        "agent_id": agent_id,
        "focus_areas": ["accuracy", "citations", "conciseness"]
    })
    assert opt_res.status_code == 200
    opt_data = opt_res.json()
    assert "diff_json" in opt_data
    opt_id = opt_data["id"]

    appr_res = client.post(f"/api/v1/workspaces/{ws_id}/prompt-optimizer/{opt_id}/approve", headers=headers)
    assert appr_res.status_code == 200

    # 12. Deployment Center & API Key
    dep_res = client.post(f"/api/v1/workspaces/{ws_id}/deployments", headers=headers, json={
        "agent_id": agent_id,
        "name": "VoiceBox Production Widget",
        "environment": "production"
    })
    assert dep_res.status_code == 201
    dep_id = dep_res.json()["id"]

    key_res = client.post(f"/api/v1/workspaces/{ws_id}/api-keys", headers=headers, json={
        "deployment_id": dep_id,
        "name": "Production Key"
    })
    assert key_res.status_code == 201
    key_data = key_res.json()
    raw_key = key_data["raw_key"]
    assert raw_key.startswith("af_live_")

    # 13. Public API Endpoint Execution
    pub_chat_res = client.post(
        f"/api/v1/public/deployments/{dep_id}/chat",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={"message": "Summarize typography rules for headings"}
    )
    assert pub_chat_res.status_code == 200
    pub_chat_data = pub_chat_res.json()
    assert "reply" in pub_chat_data
    assert pub_chat_data["tokens"] > 0

    # 14. Analytics & Audit Logs
    ana_res = client.get(f"/api/v1/workspaces/{ws_id}/analytics", headers=headers)
    assert ana_res.status_code == 200
    ana_data = ana_res.json()
    assert ana_data["total_conversations"] >= 1
    assert ana_data["total_tokens"] > 0
    assert len(ana_data["agent_distribution"]) >= 1

    audit_res = client.get(f"/api/v1/workspaces/{ws_id}/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    assert len(audit_res.json()) >= 3
