"""
Analyze Report Route — GET /analyze-report

Endpoint 2 (Complaint analysis from SwarajDesk backend).
No input required — generates the full global report automatically on call.
"""

import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import get_analyze_pipeline
from utils.sse_helpers import format_sse
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


# ─────────────────────────────────────────────────────────────────
# Streaming endpoint — GET /analyze-report/stream
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/analyze-report/stream",
    summary="Stream Analyze Report (SSE)",
    description=(
        "Streaming version of /analyze-report. Returns Server-Sent Events "
        "with progress updates and LLM token chunks in real-time. "
        "Use curl -N or EventSource to consume."
    ),
)
async def stream_analyze_report():
    """
    SSE streaming endpoint for the global analysis report.
    Emits: progress, token, phase_complete, complete, error events.
    """
    log.info("SSE stream requested for analyze-report")

    async def event_generator():
        start = time.perf_counter()
        category = "All"

        try:
            yield format_sse("pipeline_start", {
                "phase": "analyze_report",
                "category": category,
            })

            pipeline = get_analyze_pipeline()
            async for sse_chunk in pipeline.run_stream(category=category):
                yield sse_chunk

            total = round(time.perf_counter() - start, 2)
            yield format_sse("complete", {
                "success": True,
                "total_time_seconds": total,
                "category_scope": category,
                "retrieval_strategy": "Multi-Category MMR (Advanced RAG)",
            })

        except Exception as e:
            log.error(f"Stream error: {e}", exc_info=True)
            yield format_sse("error", {
                "error": "Analyze report streaming failed",
                "detail": str(e),
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
