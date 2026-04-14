import json
from datetime import datetime, timezone
from typing import List, Generator

from langchain_core.documents import Document

from models.llm.llm_loader import GeminiLLM
from models.llm.prompt_template import SURVEY_REPORT_PROMPT
from services.processor.clusterer import DocumentClusterer
from utils.json_parser import extract_json
from utils.logger import get_logger, log_step

log = get_logger("survey_report_generator")


class SurveyReportGenerator:
    """
    Generates a comprehensive survey report (JSON Report 1)
    from retrieved NGO/survey documents.
    """

    def __init__(self, llm: GeminiLLM):
        self.llm = llm
        self.clusterer = DocumentClusterer()

    @log_step("Generating survey report")
    def generate(
        self,
        category: str,
        documents: List[Document],
    ) -> dict:
        """
        Generate the survey report.

        Args:
            category: The category name
            documents: Retrieved and reranked documents

        Returns:
            Structured JSON report dict
        """
        if not documents:
            log.warning(f"No documents for survey report: {category}")
            return self._empty_report(category)

        # Build structured context
        context = self.clusterer.build_context(documents)

        # Format the prompt
        timestamp = datetime.now(timezone.utc).isoformat()
        prompt = SURVEY_REPORT_PROMPT.format(
            category=category,
            context=context,
            timestamp=timestamp,
        )

        # Generate report via LLM
        report = self.llm.generate_json(prompt)

        if not report:
            log.error(f"LLM returned empty survey report for: {category}")
            return self._empty_report(category)

        # Ensure required fields
        report.setdefault("report_type", "survey_report")
        report.setdefault("category", category)
        report.setdefault("generated_at", timestamp)

        log.info(
            f"Survey report generated: "
            f"{len(report.get('key_findings', []))} findings"
        )
        return report

    def generate_stream(
        self,
        category: str,
        documents: List[Document],
    ) -> Generator[str, None, None]:
        """
        Same as generate() but yields token chunks for streaming.

        Yields:
            str — raw LLM token chunks.
            Final yield: sentinel string "__RESULT__:<json>" with parsed report.
        """
        if not documents:
            result = self._empty_report(category)
            yield f"__RESULT__:{json.dumps(result, ensure_ascii=False)}"
            return

        context = self.clusterer.build_context(documents)
        timestamp = datetime.now(timezone.utc).isoformat()
        prompt = SURVEY_REPORT_PROMPT.format(
            category=category,
            context=context,
            timestamp=timestamp,
        )

        buffer = ""
        for chunk in self.llm.generate_json_stream(prompt):
            buffer += chunk
            yield chunk

        # Parse final JSON from accumulated buffer
        result = extract_json(buffer)
        if not result or not isinstance(result, dict):
            result = self._empty_report(category)
        else:
            result.setdefault("report_type", "survey_report")
            result.setdefault("category", category)
            result.setdefault("generated_at", timestamp)

        yield f"__RESULT__:{json.dumps(result, ensure_ascii=False)}"

    @staticmethod
    def _empty_report(category: str) -> dict:
        """Return a minimal report when no data is available."""
        return {
            "report_type": "survey_report",
            "category": category,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": f"No survey data available for category: {category}",
            "total_documents_analyzed": 0,
            "key_findings": [],
            "statistics": {
                "total_records_analyzed": 0,
                "severity_distribution": {"high": 0, "medium": 0, "low": 0},
                "geographic_coverage": [],
                "data_sources_count": 0,
            },
            "recommendations": [],
            "references": [],
        }
