"""
Analyze Report Generator — generates JSON Global Analysis Report
from a diverse set of SwarajDesk backend complaints.
"""

from datetime import datetime, timezone
from typing import List

from langchain_core.documents import Document

from models.llm.llm_loader import GeminiLLM
from models.llm.prompt_template import ANALYZE_REPORT_PROMPT
from services.processor.clusterer import DocumentClusterer
from utils.logger import get_logger, log_step

log = get_logger("analyze_report_generator")


class AnalyzeReportGenerator:
    """
    Generates an overarching SwarajDesk Global Analysis Report (JSON)
    from retrieved, diverse SwarajDesk complaint documents.
    """

    def __init__(self, llm: GeminiLLM):
        self.llm = llm
        self.clusterer = DocumentClusterer()

    @log_step("Generating global analysis report")
    def generate(
        self,
        category: str,
        documents: List[Document],
    ) -> dict:
        """
        Generate the massive overarching report.

        Args:
            category: The category scope (usually 'All' or a specific category)
            documents: Diverse set of retrieved SwarajDesk documents

        Returns:
            Structured JSON global report dict
        """
        if not documents:
            log.warning(f"No documents provided for analyze report: {category}")
            return self._empty_report(category)

        # Build structured context utilizing the clusterer to organize diverse inputs
        context = self.clusterer.build_context(documents)

        # Format the prompt
        timestamp = datetime.now(timezone.utc).isoformat()
        prompt = ANALYZE_REPORT_PROMPT.format(
            category=category,
            context=context,
            timestamp=timestamp,
        )

        # Generate report via LLM
        report = self.llm.generate_json(prompt)

        if not report:
            log.error(f"LLM returned empty global report for: {category}")
            return self._empty_report(category)

        # Ensure required top-level fields exist
        report.setdefault("report_type", "analyze_report")
        report.setdefault("category_scope", category)
        report.setdefault("generated_at", timestamp)

        # Populate total sample count manually if the LLM hallucinated it
        report["total_sample_documents_analyzed"] = len(documents)

        log.info(
            f"Global Analyze report generated: "
            f"Found {len(report.get('systemic_issues', []))} systemic issues."
        )
        return report

    @staticmethod
    def _empty_report(category: str) -> dict:
        """Return a minimal report when no data is available."""
        return {
            "report_type": "analyze_report",
            "category_scope": category,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_summary": "No data available to generate a global analysis.",
            "comprehensive_overview": f"Insufficient data found for category scope: {category}",
            "total_sample_documents_analyzed": 0,
            "systemic_issues": [],
            "categorical_breakdown": [],
            "geographic_macro_analysis": {
                "highest_volume_regions": [],
                "emerging_hotspots": [],
                "regional_disparities": "N/A"
            },
            "root_cause_analysis": [],
            "statistics_estimation": {
                "severity_distribution": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0
                },
                "top_affected_demographics": []
            },
            "strategic_recommendations": []
        }
