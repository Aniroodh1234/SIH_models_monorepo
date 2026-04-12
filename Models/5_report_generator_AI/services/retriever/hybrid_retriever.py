"""
Hybrid Retriever — combines category-aware retrieval with query expansion
and multi-strategy search for maximum recall and precision.
"""

from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

from config.settings import RETRIEVAL_TOP_K
from services.retriever.vector_retriever import VectorRetriever
from utils.constants import CATEGORY_MAP
from utils.logger import get_logger, log_step

log = get_logger("hybrid_retriever")


class HybridRetriever:
    """
    Advanced retrieval combining:
    1. Category-aware filtering (uses CATEGORY_MAP)
    2. Expanded semantic queries
    3. Dual-pass retrieval (filtered + unfiltered fallback)
    4. Deduplication
    """

    def __init__(self, vector_store: Chroma):
        self.vector_retriever = VectorRetriever(vector_store)
        self.vector_store = vector_store

    @log_step("Hybrid retrieval")
    def retrieve(
        self,
        category: str,
        query: str,
        top_k: int = RETRIEVAL_TOP_K,
        dataset_type: str = "survey",
    ) -> List[Document]:
        """
        Retrieve documents with category-aware filtering.

        Args:
            category: User-facing category name
            query: Expanded search query
            top_k: Number of documents to return
            dataset_type: "survey" or "backend"

        Returns:
            Deduplicated, relevant documents
        """
        # ── Step 1: Get dataset-specific categories ───────────────
        category_info = CATEGORY_MAP.get(category, {})

        if dataset_type == "survey":
            filter_categories = category_info.get("survey_categories", [])
        else:
            filter_categories = category_info.get("backend_categories", [])

        # ── Step 2: Filtered retrieval ────────────────────────────
        filtered_docs = []
        if filter_categories:
            filtered_docs = self.vector_retriever.retrieve(
                query=query,
                top_k=top_k * 2,  # Over-retrieve for dedup
                category_filter=filter_categories,
            )
            log.info(
                f"Filtered retrieval: {len(filtered_docs)} docs "
                f"(categories: {filter_categories[:3]}...)"
            )

        # ── Step 3: Unfiltered fallback if too few results ────────
        if len(filtered_docs) < top_k // 2:
            log.info(
                f"Only {len(filtered_docs)} filtered docs. "
                f"Adding unfiltered results..."
            )
            unfiltered_docs = self.vector_retriever.retrieve_unfiltered(
                query=query,
                top_k=top_k,
            )
            filtered_docs.extend(unfiltered_docs)

        # ── Step 4: Deduplicate ───────────────────────────────────
        unique_docs = self._deduplicate(filtered_docs)

        # ── Step 5: Trim to top_k ────────────────────────────────
        result = unique_docs[:top_k]
        log.info(
            f"Final result: {len(result)} unique documents "
            f"for '{category}' ({dataset_type})"
        )
        return result

    def _deduplicate(self, docs: List[Document]) -> List[Document]:
        """Remove duplicate documents based on content."""
        seen = set()
        unique = []

        for doc in docs:
            # Use first 200 chars as fingerprint (fast)
            fingerprint = doc.page_content[:200].strip()
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique.append(doc)

        if len(docs) != len(unique):
            log.debug(
                f"Dedup: {len(docs)} → {len(unique)} "
                f"(removed {len(docs) - len(unique)})"
            )

        return unique