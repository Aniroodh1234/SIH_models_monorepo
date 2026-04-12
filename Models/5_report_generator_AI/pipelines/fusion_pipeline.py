"""
Fusion Pipeline — orchestrates Phase 3 of report generation.

Takes JSON Report 1 + JSON Report 2 and produces JSON Report 3 (fusion analysis).
"""

import json
import time
import asyncio
from typing import AsyncGenerator

from models.llm.llm_loader import GeminiLLM
from services.report_generator.fusion_report_generator import FusionReportGenerator
from utils.sse_helpers import format_sse, sync_gen_to_async
from utils.logger import get_logger, log_step

log = get_logger("fusion_pipeline")


class FusionReportPipeline:
    """
    Pipeline for generating the Fusion Report (JSON Report 3).
    """

    def __init__(self, llm: GeminiLLM):
        self.report_generator = FusionReportGenerator(llm)

    @log_step("Fusion Report Pipeline")
    def run(
        self,
        category: str,
        survey_report: dict,
        backend_report: dict,
    ) -> dict:
        """
        Generate the fusion report from both input reports.

        Args:
            category: The category name
            survey_report: JSON Report 1
            backend_report: JSON Report 2

        Returns:
            Fusion report as JSON dict
        """
        report = self.report_generator.generate(
            category=category,
            survey_report=survey_report,
            backend_report=backend_report,
        )
        return report

    async def run_stream(
        self,
        category: str,
        survey_report: dict,
        backend_report: dict,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming version of run(). Yields SSE-formatted strings.
        """
        start = time.perf_counter()

        yield format_sse("progress", {
            "phase": "llm_generation",
            "message": "Generating fusion report with Gemini (streaming)...",
            "elapsed_s": 0,
        })

        result_dict = {}
        sync_gen = self.report_generator.generate_stream(
            category, survey_report, backend_report
        )
        async for chunk in sync_gen_to_async(sync_gen):
            if chunk.startswith("__RESULT__:"):
                result_dict = json.loads(chunk[len("__RESULT__:"):])
            else:
                yield format_sse("token", {"report": "fusion_report", "chunk": chunk})

        elapsed = round(time.perf_counter() - start, 2)
        yield format_sse("phase_complete", {
            "phase": "fusion_report",
            "elapsed_s": elapsed,
            "report": result_dict,
        })
