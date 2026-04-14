from fastapi import APIRouter

from config.vector_db_config import verify_collections
from config.settings import SURVEY_COLLECTION_NAME, BACKEND_COLLECTION_NAME

router = APIRouter()


@router.get(
    "/metrics",
    summary="Service metrics for frontend",
    tags=["System"],
)
async def get_metrics():
    """Return a small set of metrics consumed by the frontend.

    Reads collection counts from the ChromaDB persistent client via
    `verify_collections()` and returns a compact payload.
    """
    collections = verify_collections()

    survey_info = collections.get(SURVEY_COLLECTION_NAME, {})
    backend_info = collections.get(BACKEND_COLLECTION_NAME, {})

    survey_count = survey_info.get("count") if survey_info.get("exists") else 0
    backend_count = backend_info.get("count") if backend_info.get("exists") else 0

    formatted = (
        f"Docs in pipeline N/A · Survey: {survey_count} · Backend: {backend_count}"
    )


    return {
        "docs_in_pipeline": "N/A",
        "survey": survey_count,
        "backend": backend_count,
        "formatted": formatted,
    }
