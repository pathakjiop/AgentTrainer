from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.core.config import settings
from app.core.database import Base, engine
import app.models  # register all models

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="AgentTrainer Platform API",
    version="1.0.0",
    description="Enterprise API for building, evaluating, optimizing, and deploying AI agents.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "agenttrainer-platform-api",
        "version": "1.0.0"
    }
