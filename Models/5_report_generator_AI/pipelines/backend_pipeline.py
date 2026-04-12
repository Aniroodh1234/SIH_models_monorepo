"""
Backend Pipeline — orchestrates Phase 2 of report generation.

Flow: Query Expansion → Retrieve → Deduplicate → Severity Tag → Rerank → Generate Report
"""

import json
import time
import asyncio
from typing import AsyncGenerator

from langchain_chroma import Chroma

from models.llm.llm_loader import GeminiLLM
from services.retriever.hybrid_retriever import HybridRetriever
from services.reranker.reranker import Reranker
from services.processor.duplicator import DuplicateRemover
from services.processor.severity_tagger import SeverityTagger
from services.report_generator.backend_report_generator import BackendReportGenerator
from utils.constants import CATEGORY_MAP
from utils.sse_helpers import format_sse, sync_gen_to_async
from config.settings import RETRIEVAL_TOP_K, RERANKER_TOP_K
from utils.logger import get_logger, log_step

log = get_logger("backend_pipeline")


class BackendReportPipeline:
    """
    End-to-end pipeline for generating Backend Report (JSON Report 2).
    """

    def __init__(self, llm: GeminiLLM, backend_store: Chroma):
        self.llm = llm
        self.retriever = HybridRetriever(backend_store)
        self.reranker = Reranker()
        self.deduplicator = DuplicateRemover()
        self.severity_tagger = SeverityTagger()
        self.report_generator = BackendReportGenerator(llm)

    @log_step("Backend Report Pipeline")
    def run(self, category: str) -> dict:
        """
        Run the full backend report pipeline.

        Args:
            category: Resolved category name

        Returns:
            Backend report as JSON dict
        """
        # ── Step 1: Query Expansion ───────────────────────────────
        keywords = CATEGORY_MAP.get(category, {}).get("keywords", [])
        expanded_query = self.llm.expand_query(category, keywords)
        log.info(f"Expanded query: {expanded_query[:100]}...")

        # ── Step 2: Retrieve from backend collection ──────────────
        raw_docs = self.retriever.retrieve(
            category=category,
            query=expanded_query,
            top_k=RETRIEVAL_TOP_K,
            dataset_type="backend",
        )

        if not raw_docs:
            log.warning(f"No backend documents retrieved for: {category}")
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
        """
        start = time.perf_counter()
        loop = asyncio.get_event_loop()

        # Step 1: Query Expansion
        yield format_sse("progress", {
            "phase": "query_expansion",
            "message": "Expanding backend query with LLM...",
            "elapsed_s": 0,
        })
        keywords = CATEGORY_MAP.get(category, {}).get("keywords", [])
        expanded_query = await loop.run_in_executor(
            None, self.llm.expand_query, category, keywords
        )

        # Step 2: Retrieval
        yield format_sse("progress", {
            "phase": "retrieval",
            "message": "Retrieving backend complaint documents...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })
        raw_docs = await loop.run_in_executor(
            None, self.retriever.retrieve, category, expanded_query,
            RETRIEVAL_TOP_K, "backend",
        )

        if not raw_docs:
            log.warning(f"No backend documents retrieved for: {category}")
            yield format_sse("phase_complete", {
                "phase": "backend_report",
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
            "message": "Reranking backend documents with cross-encoder...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })
        reranked_docs = await loop.run_in_executor(
            None, self.reranker.rerank, expanded_query, tagged_docs,
            RERANKER_TOP_K,
        )

        # Step 6: Streaming LLM generation
        yield format_sse("progress", {
            "phase": "llm_generation",
            "message": "Generating backend report with Gemini (streaming)...",
            "elapsed_s": round(time.perf_counter() - start, 1),
        })

        result_dict = {}
        sync_gen = self.report_generator.generate_stream(category, reranked_docs)
        async for chunk in sync_gen_to_async(sync_gen):
            if chunk.startswith("__RESULT__:"):
                result_dict = json.loads(chunk[len("__RESULT__:"):])
            else:
                yield format_sse("token", {"report": "backend_report", "chunk": chunk})

        elapsed = round(time.perf_counter() - start, 2)
        yield format_sse("phase_complete", {
            "phase": "backend_report",
            "elapsed_s": elapsed,
            "report": result_dict,
        })
