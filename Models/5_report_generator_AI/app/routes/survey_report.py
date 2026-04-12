"""
Survey Report Route — POST /survey-report

Generates 3 JSON reports (survey, backend, fusion) for a given category.
"""

import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.request_schemas import SurveyReportRequest
from app.schemas.response_schema import ReportResponse, ErrorResponse
from app.dependencies import (
    get_survey_pipeline,
    get_backend_pipeline,
    get_fusion_pipeline,
)
from utils.validator import resolve_category
from utils.constants import VALID_CATEGORIES
from utils.sse_helpers import format_sse
from utils.logger import get_logger

log = get_logger("survey_route")

router = APIRouter(tags=["Survey Report"])

# Thread pool for parallel pipeline execution
_executor = ThreadPoolExecutor(max_workers=2)


@router.post(
    "/survey-report",
    response_model=ReportResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid category"},
        500: {"model": ErrorResponse, "description": "Pipeline error"},
    },
    summary="Generate Survey Report",
    description=(
        "Generates 3 JSON reports for a given category: "
        "(1) Survey/NGO Report, (2) SwarajDesk Backend Report, "
        "(3) Fusion Report combining both."
    ),
)
async def generate_survey_report(request: SurveyReportRequest):
    """
    Main endpoint for survey report generation.

    Pipeline:
    1. Resolve category (exact + fuzzy matching)
    2. Run Survey Pipeline (Report 1) and Backend Pipeline (Report 2) in parallel
    3. Run Fusion Pipeline (Report 3) using Reports 1 & 2
    4. Return all 3 reports
    """
    start_time = time.perf_counter()

    # ── Step 1: Resolve category ──────────────────────────────────
    resolved = resolve_category(request.category)

    if resolved is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Unknown category: '{request.category}'",
                "valid_categories": VALID_CATEGORIES,
                "hint": "Use one of the valid categories or a related keyword.",
            },
        )

    log.info(
        f"Category resolved: '{request.category}' → '{resolved}'"
    )

    try:
        # ── Step 2: Run Phase 1 & 2 in parallel ──────────────────
        loop = asyncio.get_running_loop()

        survey_pipeline = get_survey_pipeline()
        backend_pipeline = get_backend_pipeline()

        # Execute both pipelines concurrently using thread pool
        survey_future = loop.run_in_executor(
            _executor, survey_pipeline.run, resolved
        )
        backend_future = loop.run_in_executor(
            _executor, backend_pipeline.run, resolved
        )

        survey_report, backend_report = await asyncio.gather(
            survey_future, backend_future
        )

        phase12_time = time.perf_counter() - start_time
        log.info(f"Phase 1 & 2 completed in {phase12_time:.2f}s")

        # ── Step 3: Run Phase 3 (Fusion) ──────────────────────────
        fusion_pipeline = get_fusion_pipeline()
        fusion_report = await loop.run_in_executor(
            _executor,
            fusion_pipeline.run,
            resolved,
            survey_report,
            backend_report,
        )

        total_time = time.perf_counter() - start_time
        log.info(f"All 3 reports generated in {total_time:.2f}s")

        # ── Build response ────────────────────────────────────────
        return ReportResponse(
            success=True,
            category=request.category,
            resolved_category=resolved,
            survey_report=survey_report,
            backend_report=backend_report,
            fusion_report=fusion_report,
            pipeline_metadata={
                "total_time_seconds": round(total_time, 2),
                "phase_1_2_time_seconds": round(phase12_time, 2),
                "phase_3_time_seconds": round(total_time - phase12_time, 2),
            },
        )

    except Exception as e:
        log.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Report generation failed",
                "detail": str(e),
            },
        )


# ─────────────────────────────────────────────────────────────────
# Streaming endpoint — POST /survey-report/stream
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/survey-report/stream",
    summary="Stream Survey Report (SSE)",
    description=(
        "Streaming version of /survey-report. Returns Server-Sent Events "
        "with progress updates and LLM token chunks for all 3 report phases "
        "(survey, backend, fusion) in real-time. "
        "Phases run sequentially so tokens are not interleaved."
    ),
)
async def stream_survey_report(request: SurveyReportRequest):
    """
    SSE streaming endpoint for the triple-report generation.
    Phases: survey → backend → fusion (sequential for coherent streaming).
    """
    resolved = resolve_category(request.category)

    if resolved is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Unknown category: '{request.category}'",
                "valid_categories": VALID_CATEGORIES,
                "hint": "Use one of the valid categories or a related keyword.",
            },
        )

    log.info(f"SSE stream requested for survey-report: '{request.category}' → '{resolved}'")

    async def event_generator():
        start = time.perf_counter()
        survey_report = {}
        backend_report = {}

        try:
            # ── Phase 1: Survey Report ────────────────────────────
            yield format_sse("pipeline_start", {
                "phase": "survey_report",
                "category": resolved,
            })
            async for sse_chunk in get_survey_pipeline().run_stream(resolved):
                # Intercept phase_complete to capture the report dict
                if 'event: phase_complete' in sse_chunk:
                    data_line = sse_chunk.split("data: ", 1)[1].strip()
                    survey_report = json.loads(data_line).get("report", {})
                yield sse_chunk

            # ── Phase 2: Backend Report ───────────────────────────
            yield format_sse("pipeline_start", {
                "phase": "backend_report",
                "category": resolved,
            })
            async for sse_chunk in get_backend_pipeline().run_stream(resolved):
                if 'event: phase_complete' in sse_chunk:
                    data_line = sse_chunk.split("data: ", 1)[1].strip()
                    backend_report = json.loads(data_line).get("report", {})
                yield sse_chunk

            # ── Phase 3: Fusion Report ────────────────────────────
            yield format_sse("pipeline_start", {
                "phase": "fusion_report",
                "category": resolved,
            })
            async for sse_chunk in get_fusion_pipeline().run_stream(
                resolved, survey_report, backend_report
            ):
                yield sse_chunk

            total = round(time.perf_counter() - start, 2)
            yield format_sse("complete", {
                "success": True,
                "category": request.category,
                "resolved_category": resolved,
                "total_time_seconds": total,
            })

        except Exception as e:
            log.error(f"Stream error: {e}", exc_info=True)
            yield format_sse("error", {
                "error": "Report streaming failed",
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
