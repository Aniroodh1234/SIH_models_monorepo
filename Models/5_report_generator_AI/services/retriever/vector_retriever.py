"""
Vector Retriever — retrieves documents from a specific ChromaDB collection
using MMR (Maximum Marginal Relevance) for diversity.
"""

from typing import List, Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config.settings import MMR_FETCH_K, MMR_LAMBDA_MULT, RETRIEVAL_TOP_K
from utils.logger import get_logger, log_step

log = get_logger("vector_retriever")


class VectorRetriever:
    """
    Retrieves documents from a specific vector store collection.
    Uses MMR for result diversity + metadata filtering.
    """

    def __init__(self, vector_store: Chroma):
        self.vector_store = vector_store

    @log_step("Vector retrieval")
    def retrieve(
        self,
        query: str,
        top_k: int = RETRIEVAL_TOP_K,
        category_filter: Optional[List[str]] = None,
    ) -> List[Document]:
        """
        Retrieve documents using MMR for diversity.

        Args:
            query: Semantic search query
            top_k: Number of documents to return
            category_filter: Optional list of category names to filter by

        Returns:
            List of relevant, diverse documents
        """
        # Build filter dict for Chroma
        where_filter = None
        if category_filter and len(category_filter) > 0:
            if len(category_filter) == 1:
                where_filter = {"category": category_filter[0]}
            else:
                where_filter = {
                    "$or": [
                        {"category": cat} for cat in category_filter
                    ]
                }

        try:
            # Use MMR for diverse results — retry once on transient errors
            docs = None
            for _attempt in range(2):
                try:
                    docs = self.vector_store.max_marginal_relevance_search(
                        query=query,
                        k=top_k,
                        fetch_k=MMR_FETCH_K,
                        lambda_mult=MMR_LAMBDA_MULT,
                        filter=where_filter,
                    )
                    break
                except Exception as retry_err:
                    if _attempt == 0:
                        import time
                        log.warning(
                            f"MMR retrieval attempt 1 failed: {retry_err}. "
                            f"Retrying in 1s..."
                        )
                        time.sleep(1.0)
                    else:
                        raise retry_err

            log.info(
                f"Retrieved {len(docs)} documents "
                f"(filter: {category_filter})"
            )
            return docs

        except Exception as e:
            log.warning(f"MMR retrieval failed: {e}. Falling back to similarity search.")

            # Fallback: simple similarity search
            try:
                docs = self.vector_store.similarity_search(
                    query=query,
                    k=top_k,
                    filter=where_filter,
                )
                log.info(f"Fallback retrieved {len(docs)} documents")
                return docs
            except Exception as e2:
                log.error(f"All retrieval methods failed: {e2}")
                return []

    def retrieve_unfiltered(
        self,
        query: str,
        top_k: int = RETRIEVAL_TOP_K,
    ) -> List[Document]:
        """
        Retrieve without any metadata filtering — broader search.
        """
        return self.retrieve(query=query, top_k=top_k, category_filter=None)
