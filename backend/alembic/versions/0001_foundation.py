"""foundation"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("users", sa.Column("id", UUID(as_uuid=True), primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("full_name", sa.String(200), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("workspaces", sa.Column("id", UUID(as_uuid=True), primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("agents", sa.Column("id", UUID(as_uuid=True), primary_key=True), sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text(), nullable=False, server_default=""), sa.Column("category", sa.String(100), nullable=False, server_default="general"), sa.Column("system_prompt", sa.Text(), nullable=False, server_default="You are a helpful assistant."), sa.Column("model", sa.String(100), nullable=False, server_default="gpt-4o-mini"), sa.Column("temperature", sa.Float(), nullable=False, server_default="0.2"), sa.Column("status", sa.String(30), nullable=False, server_default="draft"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_agents_workspace_id", "agents", ["workspace_id"])
def downgrade():
    op.drop_table("agents"); op.drop_table("workspaces"); op.drop_table("users")
