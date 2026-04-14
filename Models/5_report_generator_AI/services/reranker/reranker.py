from typing import List
from langchain_core.documents import Document
from config.settings import RERANKER_MODEL_NAME, RERANKER_TOP_K
from utils.logger import get_logger, log_step

log = get_logger("reranker")

# ── Singleton cross-encoder ──────────────────────────────────────
_cross_encoder = None


def _get_cross_encoder():
    """Lazy-load the cross-encoder model (singleton)."""
    global _cross_encoder
    if _cross_encoder is None:
        log.info(f"Loading cross-encoder: {RERANKER_MODEL_NAME}")
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder(RERANKER_MODEL_NAME)
        log.info("Cross-encoder loaded.")
    return _cross_encoder


class Reranker:
    """
    Reranks documents using a cross-encoder model.
    
    The cross-encoder scores (query, document) pairs directly,
    providing more accurate relevance scoring than vector similarity alone.
    """

    def __init__(self):
        self.model = _get_cross_encoder()

    @log_step("Reranking documents")
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = RERANKER_TOP_K,
    ) -> List[Document]:
        """
        Rerank documents by cross-encoder relevance score.

        Args:
            query: The search query
            documents: List of retrieved documents
            top_k: Number of top documents to return

        Returns:
            Top-k documents sorted by relevance score (highest first)
        """
        if not documents:
            log.warning("No documents to rerank")
            return []

        if len(documents) <= top_k:
            log.info(
                f"Only {len(documents)} docs (≤ top_k={top_k}), "
                f"skipping reranking"
            )
            return documents

        # ── Create (query, document) pairs for scoring ────────────
        pairs = [
            (query, doc.page_content) for doc in documents
        ]

        # ── Score all pairs ───────────────────────────────────────
        scores = self.model.predict(pairs)

        # ── Sort by score (descending) ────────────────────────────
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # ── Log score distribution ────────────────────────────────
        top_scores = [f"{s:.3f}" for _, s in scored_docs[:5]]
        bottom_scores = [f"{s:.3f}" for _, s in scored_docs[-3:]]
        log.info(
            f"Reranked {len(documents)} → {top_k} docs. "
            f"Top scores: {top_scores}, Bottom: {bottom_scores}"
        )

        return [doc for doc, _ in scored_docs[:top_k]]
