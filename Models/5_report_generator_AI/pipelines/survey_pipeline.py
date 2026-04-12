"""
Survey Pipeline — orchestrates Phase 1 of report generation.

Flow: Query Expansion → Retrieve → Deduplicate → Severity Tag → Rerank → Generate Report
"""

import json
import time
import asyncio
from typing import List, AsyncGenerator

from langchain_chroma import Chroma
from langchain_core.documents import Document

from models.llm.llm_loader import GeminiLLM
from services.retriever.hybrid_retriever import HybridRetriever
from services.reranker.reranker import Reranker
from services.processor.duplicator import DuplicateRemover
from services.processor.severity_tagger import SeverityTagger
from services.report_generator.survey_report_generator import SurveyReportGenerator
from utils.constants import CATEGORY_MAP
from utils.sse_helpers import format_sse, sync_gen_to_async
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

    async def run_stream(self, category: str) -> AsyncGenerator[str, None]:
        """
        Streaming version of run(). Yields SSE-formatted strings.

        Yields:
            SSE strings of event types: progress, token, phase_complete
        """
        start = time.perf_counter()
        loop = asyncio.get_event_loop()

        # Step 1: Query Expansion
        yield format_sse("progress", {
            "phase": "query_expansion",
            "message": "Expanding survey query with LLM...",
            "elapsed_s": 0,
        })
        keywords = CATEGORY_MAP.get(category, {}).get("keywords", [])
        expanded_query = await loop.run_in_executor(
            None, self.llm.expand_query, category, keywords
        )

        # Step 2: Retrieval
        yield format_sse("progress", {
            "phase": "retrieval",
            "message": "Retrieving survey documents from vector store...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })
        raw_docs = await loop.run_in_executor(
            None, self.retriever.retrieve, category, expanded_query,
            RETRIEVAL_TOP_K, "survey",
        )

        if not raw_docs:
            log.warning(f"No survey documents retrieved for: {category}")
            yield format_sse("phase_complete", {
                "phase": "survey_report",
                "elapsed_s": round(time.perf_counter() - start, 2),
                "report": self.report_generator._empty_report(category),
            })
            return

        # Step 3: Deduplication
        yield format_sse("progress", {
            "phase": "deduplication",
            "message": f"Deduplicating {len(raw_docs)} documents...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })
        unique_docs = self.deduplicator.remove(raw_docs)

        # Step 4: Severity tagging
        yield format_sse("progress", {
            "phase": "severity_tagging",
            "message": "Tagging severity levels...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })
        tagged_docs = self.severity_tagger.tag(unique_docs)

        # Step 5: Reranking
        yield format_sse("progress", {
            "phase": "reranking",
            "message": "Reranking documents with cross-encoder...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })
        reranked_docs = await loop.run_in_executor(
            None, self.reranker.rerank, expanded_query, tagged_docs,
            RERANKER_TOP_K,
        )

        # Step 6: Streaming LLM generation
        yield format_sse("progress", {
            "phase": "llm_generation",
            "message": "Generating survey report with Gemini (streaming)...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })

        result_dict = {}
        sync_gen = self.report_generator.generate_stream(category, reranked_docs)
        async for chunk in sync_gen_to_async(sync_gen):
            if chunk.startswith("__RESULT__:"):
                result_dict = json.loads(chunk[len("__RESULT__:"):])
            else:
                yield format_sse("token", {"report": "survey_report", "chunk": chunk})

        elapsed = round(time.perf_counter() - start, 2)
        yield format_sse("phase_complete", {
            "phase": "survey_report",
            "elapsed_s": elapsed,
            "report": result_dict,
        })
