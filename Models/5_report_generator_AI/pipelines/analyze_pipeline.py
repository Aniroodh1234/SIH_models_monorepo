"""
Analyze Pipeline — orchestrates the global analysis of all backend complaints.

Flow: Multi-Category Expansion → Diverse MMR Retrieval → Deduplicate → Severity Tag → Generate Global Report
"""

import json
import time
import asyncio
from typing import List, AsyncGenerator

from langchain_chroma import Chroma
from langchain_core.documents import Document

from models.llm.llm_loader import GeminiLLM
from services.retriever.hybrid_retriever import HybridRetriever
from services.processor.duplicator import DuplicateRemover
from services.processor.severity_tagger import SeverityTagger
from services.report_generator.analyze_report_generator import AnalyzeReportGenerator
from utils.constants import VALID_CATEGORIES, CATEGORY_MAP
from utils.sse_helpers import format_sse, sync_gen_to_async
from utils.logger import get_logger, log_step

log = get_logger("analyze_pipeline")


class AnalyzeReportPipeline:
    """
    End-to-end pipeline for generating the Global Analysis Report.
    """

    def __init__(self, llm: GeminiLLM, backend_store: Chroma):
        self.llm = llm
        self.retriever = HybridRetriever(backend_store)
        self.deduplicator = DuplicateRemover()
        self.severity_tagger = SeverityTagger()
        self.report_generator = AnalyzeReportGenerator(llm)

    @log_step("Analyze Report Pipeline")
    def run(self, category: str, date_from: str = None, date_to: str = None) -> dict:
        """
        Run the full global analyze report pipeline.

        Args:
            category: "All" or a specific category.
            date_from: Optional start date filter (future use).
            date_to: Optional end date filter (future use).

        Returns:
            Global Analyze report as JSON dict
        """
        raw_docs: List[Document] = []

        if category.lower() == "all":
            log.info("Generating global report across ALL categories...")
            # Multi-category retrieval to ensure comprehensive diverse coverage.
            # We fetch a chunk of docs for each valid category.
            for cat in VALID_CATEGORIES:
                keywords = CATEGORY_MAP.get(cat, {}).get("keywords", [])
                expanded_query = self.llm.expand_query(cat, keywords)

                cat_docs = self.retriever.retrieve(
                    category=cat,
                    query=expanded_query,
                    top_k=15,  # 15 per category yields ~180-200 docs total
                    dataset_type="backend",
                )
                raw_docs.extend(cat_docs)
        else:
            log.info(f"Generating analyze report for specific category: {category}")
            keywords = CATEGORY_MAP.get(category, {}).get("keywords", [])
            expanded_query = self.llm.expand_query(category, keywords)

            raw_docs = self.retriever.retrieve(
                category=category,
                query=expanded_query,
                top_k=60,  # Maximize depth for a single category
                dataset_type="backend",
            )

        if not raw_docs:
            log.warning(f"No backend documents retrieved for scope: {category}")
            return self.report_generator.generate(category, [])

        # ── Step 3: Deduplicate ───────────────────────────────────
        unique_docs = self.deduplicator.remove(raw_docs)
        log.info(f"Total unique diverse documents retrieved: {len(unique_docs)}")

        # ── Step 4: Tag severity ──────────────────────────────────
        tagged_docs = self.severity_tagger.tag(unique_docs)

        # ── Step 5: Generate report ───────────────────────────────
        # Note: We bypass `reranker` because for the "Global" report, we want to ingest
        # the entire diverse subset into Gemini's massive context window without trimming it down
        # to top 10. Gemini 2.5 Pro can handle the ~150-200 documents easily.

        report = self.report_generator.generate(category, tagged_docs)

        return report

    async def run_stream(
        self,
        category: str,
        date_from: str = None,
        date_to: str = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming version of run(). Yields SSE-formatted strings.
        """
        start = time.perf_counter()
        loop = asyncio.get_event_loop()
        raw_docs: List[Document] = []

        if category.lower() == "all":
            log.info("Streaming global report across ALL categories...")
            total_cats = len(VALID_CATEGORIES)
            for idx, cat in enumerate(VALID_CATEGORIES, 1):
                yield format_sse("progress", {
                    "phase": "multi_category_retrieval",
                    "message": f"Retrieving: {cat} ({idx}/{total_cats})...",
                    "elapsed_s": round(time.perf_counter() - start, 1),
                })
                keywords = CATEGORY_MAP.get(cat, {}).get("keywords", [])
                expanded_query = await loop.run_in_executor(
                    None, self.llm.expand_query, cat, keywords
                )
                cat_docs = await loop.run_in_executor(
                    None, self.retriever.retrieve, cat, expanded_query,
                    15, "backend",
                )
                raw_docs.extend(cat_docs)
        else:
            yield format_sse("progress", {
                "phase": "retrieval",
                "message": f"Retrieving documents for: {category}...",
                "elapsed_s": round(time.perf_counter() - start, 1),
            })
            keywords = CATEGORY_MAP.get(category, {}).get("keywords", [])
            expanded_query = await loop.run_in_executor(
                None, self.llm.expand_query, category, keywords
            )
            raw_docs = await loop.run_in_executor(
                None, self.retriever.retrieve, category, expanded_query,
                60, "backend",
            )

        if not raw_docs:
            log.warning(f"No backend documents retrieved for scope: {category}")
            yield format_sse("phase_complete", {
                "phase": "analyze_report",
                "elapsed_s": round(time.perf_counter() - start, 2),
                "report": self.report_generator._empty_report(category),
            })
            return

        # Deduplication
        yield format_sse("progress", {
            "phase": "deduplication",
            "message": f"Deduplicating {len(raw_docs)} documents...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })
        unique_docs = self.deduplicator.remove(raw_docs)
        log.info(f"Total unique diverse documents: {len(unique_docs)}")

        # Severity tagging
        yield format_sse("progress", {
            "phase": "severity_tagging",
            "message": f"Tagging {len(unique_docs)} documents by severity...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })
        tagged_docs = self.severity_tagger.tag(unique_docs)

        # Streaming LLM generation
        yield format_sse("progress", {
            "phase": "llm_generation",
            "message": "Generating global analysis report with Gemini (streaming)...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })

        result_dict = {}
        sync_gen = self.report_generator.generate_stream(category, tagged_docs)
        async for chunk in sync_gen_to_async(sync_gen):
            if chunk.startswith("__RESULT__:"):
                result_dict = json.loads(chunk[len("__RESULT__:"):])
            else:
                yield format_sse("token", {"report": "analyze_report", "chunk": chunk})

        elapsed = round(time.perf_counter() - start, 2)
        yield format_sse("phase_complete", {
            "phase": "analyze_report",
            "elapsed_s": elapsed,
            "report": result_dict,
        })
