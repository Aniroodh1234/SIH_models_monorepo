"""
Analyze Report Route — GET /analyze-report

Endpoint 2 (Complaint analysis from SwarajDesk backend).
No input required — generates the full global report automatically on call.
"""

import time
from fastapi import APIRouter, HTTPException

from app.dependencies import get_analyze_pipeline
from utils.logger import get_logger

log = get_logger("analyze_route")

router = APIRouter(tags=["Analyze Report"])


@router.get(
    "/analyze-report",
    summary="Analyze Complaints Report (Global Analysis)",
    description=(
        "Generates a comprehensive global analysis report of ALL complaints "
        "lodged on the SwarajDesk backend using Advanced RAG with MMR retrieval. "
        "No input required — just call this endpoint."
    ),
)
async def analyze_report():
    """
    Endpoint 2: Global complaint analysis report.
    No request body needed — fires automatically across ALL categories.
    """
    start_time = time.perf_counter()
    category = "All"

    log.info("Received request for analyze-report — auto-running with category='All'")

    try:
        pipeline = get_analyze_pipeline()

        report = pipeline.run(category=category)

        total_time = time.perf_counter() - start_time
        log.info(f"Analyze report generated in {total_time:.2f}s")

        # Attach pipeline execution metadata
        if isinstance(report, dict):
            report["pipeline_metadata"] = {
                "total_time_seconds": round(total_time, 2),
                "category_scope": category,
                "retrieval_strategy": "Multi-Category MMR (Advanced RAG)"
            }

        return report

    except Exception as e:
        log.error(f"Global analyze pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Analyze report generation failed",
                "detail": str(e),
            },
        )
