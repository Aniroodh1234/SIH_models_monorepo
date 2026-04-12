"""
Severity Tagger — tags documents with severity levels using
keyword-based heuristics.
"""

from typing import List
from langchain_core.documents import Document

from utils.logger import get_logger, log_step

log = get_logger("severity_tagger")

# ── Severity keyword sets ─────────────────────────────────────────
HIGH_SEVERITY_KEYWORDS = {
    "death", "died", "fatal", "collapse", "collapsed", "dangerous",
    "hazardous", "toxic", "contaminated", "emergency", "critical",
    "severe", "urgent", "life-threatening", "accident", "major",
    "outbreak", "epidemic", "flooding", "fire", "explosion",
    "unsafe", "no water", "no electricity", "complete failure",
    "disease", "injury", "injured", "casualty",
}

MEDIUM_SEVERITY_KEYWORDS = {
    "broken", "damaged", "poor", "complaint", "inadequate",
    "insufficient", "irregular", "delay", "delayed", "pending",
    "shortage", "overflow", "blocked", "clogged", "frequent",
    "repeated", "missing", "absent", "stray", "unhygienic",
    "dirty", "overflowing", "pothole", "crack", "leak",
    "disruption", "low quality", "unpaved",
}

LOW_SEVERITY_KEYWORDS = {
    "maintenance", "minor", "cosmetic", "improvement", "moderate",
    "occasional", "suggestion", "request", "feedback", "review",
    "assessment", "survey", "general", "routine", "normal",
}


class SeverityTagger:
    """
    Tags documents with severity levels based on content keywords.
    """

    @log_step("Tagging severity")
    def tag(self, documents: List[Document]) -> List[Document]:
        """
        Tag each document with a severity level in its metadata.

        Args:
            documents: List of documents to tag

        Returns:
            Documents with 'severity' added to metadata
        """
        for doc in documents:
            severity = self._compute_severity(doc.page_content)
            doc.metadata["severity"] = severity

        # Log distribution
        dist = {"high": 0, "medium": 0, "low": 0}
        for doc in documents:
            dist[doc.metadata["severity"]] += 1

        log.info(f"Severity distribution: {dist}")
        return documents

    def _compute_severity(self, text: str) -> str:
        """Determine severity based on keyword frequency."""
        text_lower = text.lower()
        tokens = set(text_lower.split())

        high_score = len(tokens & HIGH_SEVERITY_KEYWORDS)
        medium_score = len(tokens & MEDIUM_SEVERITY_KEYWORDS)
        low_score = len(tokens & LOW_SEVERITY_KEYWORDS)

        # Also check for multi-word phrases
        for phrase in HIGH_SEVERITY_KEYWORDS:
            if " " in phrase and phrase in text_lower:
                high_score += 2

        for phrase in MEDIUM_SEVERITY_KEYWORDS:
            if " " in phrase and phrase in text_lower:
                medium_score += 1

        if high_score >= 1:
            return "high"
        elif medium_score >= 1:
            return "medium"
        else:
            return "low"
