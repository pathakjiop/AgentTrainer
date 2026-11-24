import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid
from app.core.database import Base

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    agent_version: Mapped[int] = mapped_column(default=1)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="completed")  # pending, running, completed, failed
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    grade: Mapped[str] = mapped_column(String(50), default="Needs improvement")
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="evaluation_runs")
    agent = relationship("Agent", back_populates="evaluation_runs")
    dataset = relationship("Dataset", back_populates="evaluation_runs")
    results = relationship("EvaluationResult", back_populates="run", cascade="all, delete-orphan")

class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True)
    example_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    question: Mapped[str] = mapped_column(Text)
    expected_answer: Mapped[str] = mapped_column(Text)
    actual_answer: Mapped[str] = mapped_column(Text)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    completeness: Mapped[float] = mapped_column(Float, default=0.0)
    instruction_following: Mapped[float] = mapped_column(Float, default=0.0)
    hallucination_risk: Mapped[float] = mapped_column(Float, default=0.0)
    safety: Mapped[float] = mapped_column(Float, default=1.0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    feedback: Mapped[str] = mapped_column(Text, default="")
    suggestions_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    run = relationship("EvaluationRun", back_populates="results")
