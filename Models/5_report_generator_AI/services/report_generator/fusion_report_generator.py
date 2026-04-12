"""
Fusion Report Generator — generates JSON Report 3 by fusing
the survey report and backend report into a comprehensive analysis.
"""

import json
from datetime import datetime, timezone
from typing import Generator

from models.llm.llm_loader import GeminiLLM
from models.llm.prompt_template import FUSION_REPORT_PROMPT
from utils.json_parser import extract_json
from utils.logger import get_logger, log_step

log = get_logger("fusion_report_generator")


class FusionReportGenerator:
    """
    Generates a fusion report (JSON Report 3) by combining
    insights from Report 1 (survey) and Report 2 (backend).
    """

    def __init__(self, llm: GeminiLLM):
        self.llm = llm

    @log_step("Generating fusion report")
    def generate(
        self,
        category: str,
        survey_report: dict,
        backend_report: dict,
    ) -> dict:
        """
        Generate the fusion report.

        Args:
            category: The category name
            survey_report: JSON Report 1 (survey/NGO data)
            backend_report: JSON Report 2 (SwarajDesk data)

        Returns:
            Structured fusion JSON report dict
        """
        # Format both reports as readable JSON strings for the LLM
        survey_json = json.dumps(survey_report, indent=2, ensure_ascii=False)
        backend_json = json.dumps(backend_report, indent=2, ensure_ascii=False)

        # Format prompt
        timestamp = datetime.now(timezone.utc).isoformat()
        prompt = FUSION_REPORT_PROMPT.format(
            category=category,
            survey_report=survey_json,
            backend_report=backend_json,
            timestamp=timestamp,
        )

        # Generate report via LLM
        report = self.llm.generate_json(prompt)

        if not report:
            log.error(f"LLM returned empty fusion report for: {category}")
            return self._empty_report(category)

        # Ensure required fields
        report.setdefault("report_type", "fusion_report")
        report.setdefault("category", category)
        report.setdefault("generated_at", timestamp)

        log.info(
            f"Fusion report generated: "
            f"{len(report.get('unified_findings', []))} unified findings"
        )
        return report

    def generate_stream(
        self,
        category: str,
        survey_report: dict,
        backend_report: dict,
    ) -> Generator[str, None, None]:
        """
        Same as generate() but yields token chunks for streaming.

        Yields:
            str — raw LLM token chunks.
            Final yield: sentinel string "__RESULT__:<json>" with parsed report.
        """
        survey_json = json.dumps(survey_report, indent=2, ensure_ascii=False)
        backend_json = json.dumps(backend_report, indent=2, ensure_ascii=False)

        timestamp = datetime.now(timezone.utc).isoformat()
        prompt = FUSION_REPORT_PROMPT.format(
            category=category,
            survey_report=survey_json,
            backend_report=backend_json,
            timestamp=timestamp,
        )

        buffer = ""
        for chunk in self.llm.generate_json_stream(prompt):
            buffer += chunk
            yield chunk

        result = extract_json(buffer)
        if not result or not isinstance(result, dict):
            result = self._empty_report(category)
        else:
            result.setdefault("report_type", "fusion_report")
            result.setdefault("category", category)
            result.setdefault("generated_at", timestamp)

        yield f"__RESULT__:{json.dumps(result, ensure_ascii=False)}"

    @staticmethod
    def _empty_report(category: str) -> dict:
        """Return a minimal fusion report when generation fails."""
        return {
            "report_type": "fusion_report",
            "category": category,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": (
                f"Unable to generate fusion report for "
                f"category: {category}"
            ),
            "cross_reference_analysis": {
                "corroborated_findings": [],
                "survey_only_findings": [],
                "backend_only_findings": [],
            },
            "unified_findings": [],
            "combined_statistics": {},
            "gap_analysis": {},
            "prioritized_recommendations": [],
            "references": {
                "survey_sources": [],
                "backend_sources": [],
            },
        }
