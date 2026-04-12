"""
Duplicate Remover — removes near-duplicate documents using
content fingerprinting and Jaccard similarity.
"""

from typing import List
from langchain_core.documents import Document

from utils.logger import get_logger, log_step

log = get_logger("duplicator")


class DuplicateRemover:
    """
    Removes near-duplicate documents from a list.
    Uses token-level Jaccard similarity for fuzzy matching.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Jaccard similarity above which
                                  docs are considered duplicates (0-1).
        """
        self.threshold = similarity_threshold

    @log_step("Removing duplicates")
    def remove(self, documents: List[Document]) -> List[Document]:
        """
        Remove near-duplicate documents.

        Args:
            documents: List of documents to deduplicate

        Returns:
            Deduplicated list of documents
        """
        if len(documents) <= 1:
            return documents

        unique_docs = []
        unique_token_sets = []

        for doc in documents:
            tokens = self._tokenize(doc.page_content)

            is_duplicate = False
            for existing_tokens in unique_token_sets:
                similarity = self._jaccard_similarity(tokens, existing_tokens)
                if similarity >= self.threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_docs.append(doc)
                unique_token_sets.append(tokens)

        removed = len(documents) - len(unique_docs)
        if removed > 0:
            log.info(
                f"Removed {removed} near-duplicates "
                f"({len(documents)} → {len(unique_docs)})"
            )

        return unique_docs

    @staticmethod
    def _tokenize(text: str) -> set:
        """Simple whitespace tokenization + lowering."""
        return set(text.lower().split())

    @staticmethod
    def _jaccard_similarity(set_a: set, set_b: set) -> float:
        """Compute Jaccard similarity between two token sets."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
