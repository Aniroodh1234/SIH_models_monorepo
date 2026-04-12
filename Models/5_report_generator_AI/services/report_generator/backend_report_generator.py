"""
Backend Report Generator — generates JSON Report 2 from SwarajDesk data.
"""

from datetime import datetime, timezone
from typing import List

from langchain_core.documents import Document

from models.llm.llm_loader import GeminiLLM
from models.llm.prompt_template import BACKEND_REPORT_PROMPT
from services.processor.clusterer import DocumentClusterer
from utils.logger import get_logger, log_step

log = get_logger("backend_report_generator")


class BackendReportGenerator:
    """
    Generates a SwarajDesk backend complaint analysis report (JSON Report 2)
    from retrieved SwarajDesk documents.
    """

    def __init__(self, llm: GeminiLLM):
        self.llm = llm
        self.clusterer = DocumentClusterer()

    @log_step("Generating backend report")
    def generate(
        self,
        category: str,
        documents: List[Document],
    ) -> dict:
        """
        Generate the backend report.

        Args:
            category: The category name
            documents: Retrieved and reranked SwarajDesk documents

        Returns:
            Structured JSON report dict
        """
        if not documents:
            log.warning(f"No documents for backend report: {category}")
            return self._empty_report(category)

        # Build structured context
        context = self.clusterer.build_context(documents)

        # Format the prompt
        timestamp = datetime.now(timezone.utc).isoformat()
        prompt = BACKEND_REPORT_PROMPT.format(
            category=category,
            context=context,
            timestamp=timestamp,
        )

        # Generate report via LLM
        report = self.llm.generate_json(prompt)

        if not report:
            log.error(f"LLM returned empty backend report for: {category}")
            return self._empty_report(category)

        # Ensure required fields
        report.setdefault("report_type", "backend_report")
        report.setdefault("category", category)
        report.setdefault("generated_at", timestamp)

        log.info(
            f"Backend report generated: "
            f"{len(report.get('key_findings', []))} findings"
        )
        return report

    @staticmethod
    def _empty_report(category: str) -> dict:
        """Return a minimal report when no data is available."""
        return {
            "report_type": "backend_report",
            "category": category,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": (
                f"No SwarajDesk complaint data available for "
                f"category: {category}"
            ),
            "total_documents_analyzed": 0,
            "key_findings": [],
            "complaint_analysis": {
                "total_complaints_analyzed": 0,
                "top_issues": [],
                "geographic_hotspots": [],
            },
            "statistics": {
                "total_records_analyzed": 0,
                "severity_distribution": {"high": 0, "medium": 0, "low": 0},
                "geographic_coverage": [],
            },
            "urgent_issues": [],
            "recommendations": [],
            "references": [],
        }
