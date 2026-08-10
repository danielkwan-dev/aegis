from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analysis, dashboard, ingestion
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Demo-scale: create tables directly on boot rather than running Alembic
    # migrations. Fine while the schema is still moving — worth switching to
    # real migrations once the schema stabilizes ahead of a first deploy.
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()

app = FastAPI(title="Aegis — Personal Privacy Intelligence Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router)
app.include_router(analysis.router)
app.include_router(dashboard.router)
