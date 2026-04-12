"""
Document Clusterer — groups retrieved documents by sub-themes
to provide structured input for report generation.
"""

from typing import List, Dict
from collections import defaultdict
from langchain_core.documents import Document

from utils.logger import get_logger, log_step

log = get_logger("clusterer")


class DocumentClusterer:
    """
    Groups documents by category and source type for structured
    context building.
    """

    @log_step("Clustering documents")
    def cluster(self, documents: List[Document]) -> Dict[str, List[Document]]:
        """
        Cluster documents by their category metadata.

        Args:
            documents: List of documents to cluster

        Returns:
            Dict mapping category -> list of documents
        """
        clusters = defaultdict(list)

        for doc in documents:
            category = doc.metadata.get("category", "uncategorized")
            clusters[category].append(doc)

        log.info(
            f"Clustered {len(documents)} docs into "
            f"{len(clusters)} groups: "
            f"{dict((k, len(v)) for k, v in clusters.items())}"
        )

        return dict(clusters)

    @log_step("Building context string")
    def build_context(
        self,
        documents: List[Document],
        max_chars: int = 30000,
    ) -> str:
        """
        Build a structured context string from documents for LLM input.

        Organizes documents by category with metadata annotations.
        Truncates to max_chars to stay within LLM context limits.

        Args:
            documents: List of documents
            max_chars: Maximum character limit for the context

        Returns:
            Formatted context string
        """
        clusters = self.cluster(documents)
        context_parts = []
        total_chars = 0

        for category, docs in clusters.items():
            section_header = f"\n--- Category: {category} ({len(docs)} records) ---\n"
            context_parts.append(section_header)
            total_chars += len(section_header)

            for i, doc in enumerate(docs, 1):
                # Build metadata line
                meta = doc.metadata
                meta_parts = []

                if meta.get("source_type"):
                    meta_parts.append(f"Source: {meta['source_type']}")
                if meta.get("source_url"):
                    meta_parts.append(f"URL: {meta['source_url']}")
                if meta.get("severity"):
                    meta_parts.append(f"Severity: {meta['severity']}")
                if meta.get("state"):
                    location_parts = []
                    for field in ["city", "district", "state"]:
                        if meta.get(field):
                            location_parts.append(meta[field])
                    if location_parts:
                        meta_parts.append(
                            f"Location: {', '.join(location_parts)}"
                        )
                if meta.get("respondent_age"):
                    meta_parts.append(f"Age: {meta['respondent_age']}")
                if meta.get("respondent_gender"):
                    meta_parts.append(f"Gender: {meta['respondent_gender']}")

                meta_line = " | ".join(meta_parts) if meta_parts else ""
                entry = f"\n[Document {i}] {meta_line}\n{doc.page_content}\n"

                if total_chars + len(entry) > max_chars:
                    context_parts.append(
                        f"\n... (truncated, {len(docs) - i} more documents) ..."
                    )
                    break

                context_parts.append(entry)
                total_chars += len(entry)

        context = "".join(context_parts)
        log.info(
            f"Context built: {len(context)} chars from "
            f"{len(documents)} documents"
        )
        return context
