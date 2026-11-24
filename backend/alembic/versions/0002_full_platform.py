"""full platform schema

Revision ID: 0002_full_platform
Revises: 0001_foundation
Create Date: 2026-11-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0002_full_platform"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add missing columns to users
    op.add_column("users", sa.Column("role", sa.String(50), nullable=False, server_default="member"))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    # 2. Add missing columns to agents
    op.add_column("agents", sa.Column("avatar", sa.String(200), nullable=False, server_default=""))
    op.add_column("agents", sa.Column("provider", sa.String(50), nullable=False, server_default="mock"))
    op.add_column("agents", sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="2048"))
    op.add_column("agents", sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"))
    op.add_column("agents", sa.Column("role_description", sa.Text(), nullable=False, server_default=""))
    op.add_column("agents", sa.Column("personality", sa.String(200), nullable=False, server_default="Professional, concise, accurate"))
    op.add_column("agents", sa.Column("restrictions", sa.Text(), nullable=False, server_default=""))
    op.add_column("agents", sa.Column("response_format", sa.String(50), nullable=False, server_default="markdown"))
    op.add_column("agents", sa.Column("tools_config", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("agents", sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"))

    # 3. Workspace members
    op.create_table(
        "workspace_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])

    # 4. Agent versions
    op.create_table(
        "agent_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("configuration_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("change_summary", sa.String(500), nullable=False, server_default="Updated configuration"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_versions_agent_id", "agent_versions", ["agent_id"])

    # 5. Knowledge bases
    op.create_table(
        "knowledge_bases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_bases_workspace_id", "knowledge_bases", ["workspace_id"])

    # 6. Agent knowledge base links
    op.create_table(
        "agent_knowledge_bases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("knowledge_base_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_knowledge_bases_agent_id", "agent_knowledge_bases", ["agent_id"])
    op.create_index("ix_agent_knowledge_bases_knowledge_base_id", "agent_knowledge_bases", ["knowledge_base_id"])

    # 7. Documents
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("knowledge_base_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ready"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_knowledge_base_id", "documents", ["knowledge_base_id"])

    # 8. Document chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("embedding_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # 9. Conversations
    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default="New Conversation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])
    op.create_index("ix_conversations_agent_id", "conversations", ["agent_id"])

    # 10. Messages
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cost_est", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("debug_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # 11. Datasets
    op.create_table(
        "datasets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_datasets_workspace_id", "datasets", ["workspace_id"])

    # 12. Dataset examples
    op.create_table(
        "dataset_examples",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("reference_context", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(100), nullable=False, server_default="general"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_dataset_examples_dataset_id", "dataset_examples", ["dataset_id"])

    # 13. Evaluation runs
    op.create_table(
        "evaluation_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="completed"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("grade", sa.String(50), nullable=False, server_default="Needs improvement"),
        sa.Column("summary_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_runs_workspace_id", "evaluation_runs", ["workspace_id"])
    op.create_index("ix_evaluation_runs_agent_id", "evaluation_runs", ["agent_id"])
    op.create_index("ix_evaluation_runs_dataset_id", "evaluation_runs", ["dataset_id"])

    # 14. Evaluation results
    op.create_table(
        "evaluation_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("example_id", UUID(as_uuid=True), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("actual_answer", sa.Text(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("relevance", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("completeness", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("instruction_following", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("hallucination_risk", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("safety", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("suggestions_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_results_run_id", "evaluation_results", ["run_id"])

    # 15. Prompt optimizations
    op.create_table(
        "prompt_optimizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_prompt", sa.Text(), nullable=False),
        sa.Column("proposed_prompt", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("diff_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("score_delta", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_prompt_optimizations_workspace_id", "prompt_optimizations", ["workspace_id"])
    op.create_index("ix_prompt_optimizations_agent_id", "prompt_optimizations", ["agent_id"])

    # 16. Deployments
    op.create_table(
        "deployments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False, server_default="production"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("widget_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deployments_workspace_id", "deployments", ["workspace_id"])
    op.create_index("ix_deployments_agent_id", "deployments", ["agent_id"])

    # 17. API keys
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deployment_id", UUID(as_uuid=True), sa.ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("scopes", sa.String(200), nullable=False, server_default="chat:read,chat:write"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_workspace_id", "api_keys", ["workspace_id"])
    op.create_index("ix_api_keys_deployment_id", "api_keys", ["deployment_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    # 18. Usage events
    op.create_table(
        "usage_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("deployment_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_usage_events_workspace_id", "usage_events", ["workspace_id"])
    op.create_index("ix_usage_events_agent_id", "usage_events", ["agent_id"])
    op.create_index("ix_usage_events_deployment_id", "usage_events", ["deployment_id"])

    # 19. Audit logs
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_workspace_id", "audit_logs", ["workspace_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("usage_events")
    op.drop_table("api_keys")
    op.drop_table("deployments")
    op.drop_table("prompt_optimizations")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_table("dataset_examples")
    op.drop_table("datasets")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("agent_knowledge_bases")
    op.drop_table("knowledge_bases")
    op.drop_table("agent_versions")
    op.drop_table("workspace_members")
    
    op.drop_column("agents", "current_version")
    op.drop_column("agents", "tools_config")
    op.drop_column("agents", "response_format")
    op.drop_column("agents", "restrictions")
    op.drop_column("agents", "personality")
    op.drop_column("agents", "role_description")
    op.drop_column("agents", "timeout_seconds")
    op.drop_column("agents", "max_tokens")
    op.drop_column("agents", "provider")
    op.drop_column("agents", "avatar")
    
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
