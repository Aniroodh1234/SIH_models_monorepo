"""
SwarajDesk AI Report Generator — FastAPI Application

Endpoints:
  POST /survey-report   → Generates 3 JSON reports (survey + backend + fusion)
  GET  /health          → Health check
  GET  /categories      → List valid categories
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.survey_report import router as survey_router
from config.vector_db_config import verify_collections
from config.settings import LLM_MODEL_NAME
from utils.constants import VALID_CATEGORIES
from utils.logger import get_logger

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # ── Startup ───────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("[START] SwarajDesk AI Report Generator -- Starting Up")
    log.info("=" * 60)

    # Verify vector stores exist
    collections = verify_collections()
    for name, info in collections.items():
        if info.get("exists"):
            log.info(f"[OK] {name}: {info['count']} records")
        else:
            log.warning(
                f"[WARN] {name}: NOT FOUND. "
                f"Run: python scripts/build_embeddings.py"
            )

    log.info(f"LLM Model: {LLM_MODEL_NAME}")
    log.info(f"Categories: {len(VALID_CATEGORIES)}")
    log.info("=" * 60)

    yield

    # ── Shutdown ──────────────────────────────────────────────────
    log.info("[STOP] Shutting down...")


# ── App Factory ───────────────────────────────────────────────────
app = FastAPI(
    title="SwarajDesk AI Report Generator",
    description=(
        "Intelligent RAG-based report generation system that produces "
        "comprehensive survey reports from NGO data and SwarajDesk "
        "citizen complaints."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ─────────────────────────────────────────────
app.include_router(survey_router)


# ── Utility Endpoints ────────────────────────────────────────────
@app.get(
    "/health",
    summary="Health Check",
    tags=["System"],
)
async def health_check():
    """Check system health and vector store status."""
    collections = verify_collections()
    return {
        "status": "healthy",
        "model": LLM_MODEL_NAME,
        "vector_stores": collections,
        "categories_count": len(VALID_CATEGORIES),
    }


@app.get(
    "/categories",
    summary="List Valid Categories",
    tags=["System"],
)
async def list_categories():
    """Return the list of valid categories for report generation."""
    return {
        "categories": VALID_CATEGORIES,
        "count": len(VALID_CATEGORIES),
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — API information."""
    return {
        "name": "SwarajDesk AI Report Generator",
        "version": "1.0.0",
        "endpoints": {
            "POST /survey-report": "Generate 3 JSON reports for a category",
            "GET /health": "System health check",
            "GET /categories": "List valid categories",
        },
    }
