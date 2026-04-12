"""
Survey Pipeline — orchestrates Phase 1 of report generation.

Flow: Query Expansion → Retrieve → Deduplicate → Severity Tag → Rerank → Generate Report
"""

from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document

from models.llm.llm_loader import GeminiLLM
from services.retriever.hybrid_retriever import HybridRetriever
from services.reranker.reranker import Reranker
from services.processor.duplicator import DuplicateRemover
from services.processor.severity_tagger import SeverityTagger
from services.report_generator.survey_report_generator import SurveyReportGenerator
from utils.constants import CATEGORY_MAP
from config.settings import RETRIEVAL_TOP_K, RERANKER_TOP_K
from utils.logger import get_logger, log_step

log = get_logger("survey_pipeline")


class SurveyReportPipeline:
    """
    End-to-end pipeline for generating Survey Report (JSON Report 1).
    """

    def __init__(self, llm: GeminiLLM, survey_store: Chroma):
        self.llm = llm
        self.retriever = HybridRetriever(survey_store)
        self.reranker = Reranker()
        self.deduplicator = DuplicateRemover()
        self.severity_tagger = SeverityTagger()
        self.report_generator = SurveyReportGenerator(llm)

    @log_step("Survey Report Pipeline")
    def run(self, category: str) -> dict:
        """
        Run the full survey report pipeline.

        Args:
            category: Resolved category name

        Returns:
            Survey report as JSON dict
        """
        # ── Step 1: Query Expansion ───────────────────────────────
        keywords = CATEGORY_MAP.get(category, {}).get("keywords", [])
        expanded_query = self.llm.expand_query(category, keywords)
        log.info(f"Expanded query: {expanded_query[:100]}...")

        # ── Step 2: Retrieve from survey collection ───────────────
        raw_docs = self.retriever.retrieve(
            category=category,
            query=expanded_query,
            top_k=RETRIEVAL_TOP_K,
            dataset_type="survey",
        )

        if not raw_docs:
            log.warning(f"No survey documents retrieved for: {category}")
            return self.report_generator.generate(category, [])

        # ── Step 3: Deduplicate ───────────────────────────────────
        unique_docs = self.deduplicator.remove(raw_docs)

        # ── Step 4: Tag severity ──────────────────────────────────
        tagged_docs = self.severity_tagger.tag(unique_docs)

        # ── Step 5: Rerank ────────────────────────────────────────
        reranked_docs = self.reranker.rerank(
            query=expanded_query,
            documents=tagged_docs,
            top_k=RERANKER_TOP_K,
        )

        # ── Step 6: Generate report ───────────────────────────────
        report = self.report_generator.generate(category, reranked_docs)

        return report
