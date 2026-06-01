"""Marginalia FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from marginalia.api.routes import analyze, conference, history, reviewer
from marginalia.api.routes import v1, crosstrack
from marginalia.config import settings
from marginalia.data.db import db
from marginalia.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events."""
    logger.info("Marginalia starting up...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Embedding model: {settings.embedding_model}")
    await db.init()
    logger.info("Marginalia ready.")
    yield
    logger.info("Marginalia shutting down...")


app = FastAPI(
    title="Marginalia API",
    description="""
## Marginalia — AI Peer Review Detection

Detect AI-generated peer reviews via 3-layer signal triangulation.

### Detection Layers
- **Specificity Index** — anchor density (equations, figures, sections)
- **Asymmetry Score** — abstract vs body grounding
- **Batch DNA** — structural fingerprint clustering

### Public API (v1)
Rate-limited endpoints for external integrations: `/api/v1/`

### Internal API
Full-featured endpoints: `/api/analyze/`, `/api/scan/`, `/api/reviewer/`
""",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting (must be added before CORS)
app.add_middleware(RateLimitMiddleware, enabled=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Internal API routes
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(conference.router, prefix="/api", tags=["conference"])
app.include_router(reviewer.router, prefix="/api", tags=["reviewer"])
app.include_router(history.router, prefix="/api", tags=["history"])

# Public API v1
app.include_router(v1.router, prefix="/api/v1", tags=["public-api-v1"])

# Cross-track extension (Track G)
app.include_router(crosstrack.router, prefix="/api", tags=["cross-track"])


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0", "service": "marginalia"}


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Marginalia API",
        "docs": "/docs",
        "health": "/health",
        "v1": "/api/v1/health",
    }
