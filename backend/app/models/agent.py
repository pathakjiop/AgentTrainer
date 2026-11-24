import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(100), default="general")
    avatar: Mapped[str] = mapped_column(String(200), default="")
    model: Mapped[str] = mapped_column(String(100), default="gpt-4o-mini")
    provider: Mapped[str] = mapped_column(String(50), default="mock")
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft, active, paused, archived
    
    # Prompting & instructions
    system_prompt: Mapped[str] = mapped_column(Text, default="You are a helpful assistant.")
    role_description: Mapped[str] = mapped_column(Text, default="")
    personality: Mapped[str] = mapped_column(String(200), default="Professional, concise, accurate")
    restrictions: Mapped[str] = mapped_column(Text, default="")
    response_format: Mapped[str] = mapped_column(String(50), default="markdown")
    tools_config: Mapped[dict] = mapped_column(JSON, default=dict)
    
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    workspace = relationship("Workspace", back_populates="agents")
    versions = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan", order_by="AgentVersion.version_number.desc()")
    knowledge_base_links = relationship("AgentKnowledgeBase", back_populates="agent", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
    evaluation_runs = relationship("EvaluationRun", back_populates="agent", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="agent", cascade="all, delete-orphan")

class AgentVersion(Base):
    __tablename__ = "agent_versions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    configuration_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    change_summary: Mapped[str] = mapped_column(String(500), default="Updated configuration")
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    agent = relationship("Agent", back_populates="versions")
