from typing import List
import asyncio

from app.models.schemas import (
    ModerationRequest,
    ModerationResult,
    FlaggedSpan,
)
from app.services.toxicity_api import get_toxicity_score
from app.services.llm_extractor import call_groq_llm_for_phrases, build_spans_from_phrases



def preprocess_text(text: str) -> str:
    """
    Basic text normalization step.
    Later we will:
      - normalize whitespace
      - unify quotes, punctuation
      - maybe standardize leetspeak (e.g., 'm@dar' -> 'madar')
      - normalize Unicode for Hindi/Odia
    For now, return as-is.
    """
    # TODO: implement actual normalization later
    return text

def _normalize_and_merge_spans(
    spans: List[FlaggedSpan],
    text_length: int,
) -> List[FlaggedSpan]:
    """
    Ensure spans are:
      - within [0, text_length]
      - sorted by start
      - non-overlapping (merge if needed)

    This makes masking logic robust even if detector returns messy spans.
    """

    if not spans:
        return []

    # 1) Clamp and filter invalid spans
    cleaned: List[FlaggedSpan] = []
    for span in spans:
        start = max(0, min(span.start, text_length))
        end = max(0, min(span.end, text_length))
        if end <= start:
            continue  # ignore empty / invalid spans

        # Make a copy with clamped indices
        cleaned.append(
            FlaggedSpan(
                start=start,
                end=end,
                original=span.original,
                masked=span.masked,
                lang=span.lang,
                category=span.category,
                severity=span.severity,
                confidence=span.confidence,
            )
        )

    if not cleaned:
        return []

    # 2) Sort by start index
    cleaned.sort(key=lambda s: s.start)

    # 3) Merge overlapping or touching spans
    merged: List[FlaggedSpan] = []
    current = cleaned[0]

    for nxt in cleaned[1:]:
        if nxt.start <= current.end:  # overlap or directly touching
            # Extend current span to cover both
            new_end = max(current.end, nxt.end)
            # Keep the same masked/original from current; we don't care which
            current = FlaggedSpan(
                start=current.start,
                end=new_end,
                original=current.original,
                masked=current.masked,
                lang=current.lang,
                category=current.category,
                severity=current.severity,
                confidence=current.confidence,
            )
        else:
            merged.append(current)
            current = nxt

    merged.append(current)
    return merged


TOXICITY_THRESHOLD = 0.55  # tweak if needed


def detect_abuse_spans(normalized_text: str) -> List[FlaggedSpan]:
    toxicity = asyncio.run(get_toxicity_score(normalized_text))

    # If HF says low toxicity, still check LLM (for Hindi/Hinglish/Odia)
    if toxicity < TOXICITY_THRESHOLD:
        parsed = asyncio.run(call_groq_llm_for_phrases(normalized_text))
        spans = build_spans_from_phrases(normalized_text, parsed)
        return spans

    # If HF says high toxicity → use LLM too
    parsed = asyncio.run(call_groq_llm_for_phrases(normalized_text))
    spans = build_spans_from_phrases(normalized_text, parsed)

    if spans:
        for s in spans:
            if s.confidence is None:
                s.confidence = float(toxicity)
        return spans

    # If everything fails but toxicity high → fallback
    return [
        FlaggedSpan(
            start=0,
            end=len(normalized_text),
            original=normalized_text,
            masked="******",
            lang=None,
            category="toxic",
            severity="medium",
            confidence=float(toxicity),
        )
    ]


def apply_masking(original_text: str, spans: List[FlaggedSpan]) -> str:
    """
    Build clean_text by replacing each abusive span with a masked version.
    - Uses '******' by default if span.masked is None.
    - Handles multiple spans and overlaps safely.
    """
    if not spans:
        return original_text

    text_length = len(original_text)

    # 1) Normalize & merge spans
    merged_spans = _normalize_and_merge_spans(spans, text_length)

    # 2) Reconstruct string
    parts: List[str] = []
    cursor = 0

    for span in merged_spans:
        # Add text before the span
        if span.start > cursor:
            parts.append(original_text[cursor:span.start])

        # Decide what to use as masked token
        masked_value = span.masked if span.masked is not None else "******"

        # Optionally: ensure masked length equals original length (if you want)
        # Here I'm using constant "******" as per your requirement.

        parts.append(masked_value)

        # Move cursor after this span
        cursor = span.end

    # Add remaining text after last span
    if cursor < text_length:
        parts.append(original_text[cursor:])

    return "".join(parts)



def compute_overall_severity(spans: List[FlaggedSpan]) -> str:
    """
    Decide overall severity from individual spans.
    Priority:
        if any span.severity == "high"   -> "high"
        elif any == "medium"             -> "medium"
        elif any == "low"                -> "low"
        else                             -> "none"
    For now, if spans exist but have no severity set, we return "medium".
    """
    if not spans:
        return "none"

    severities = {s.severity for s in spans if s.severity is not None}

    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    if "low" in severities:
        return "low"

    # Default if spans exist but no severity info present
    return "medium"



def run_moderation(req: ModerationRequest) -> ModerationResult:
    """
    Main orchestration function for moderation.
    This is the single function called by the API layer.
    """

    # 1) Preprocess / normalize text
    normalized = preprocess_text(req.text)

    # 2) Detect abusive words/phrases (returns spans)
    spans = detect_abuse_spans(normalized)

    has_abuse = len(spans) > 0

    # 3) Build cleaned text by masking abusive parts
    clean_text = apply_masking(req.text, spans) if has_abuse else req.text

    # 4) Compute overall severity
    severity = compute_overall_severity(spans)

    # 5) Build final response
    return ModerationResult(
        has_abuse=has_abuse,
        original_text=req.text,
        clean_text=clean_text,
        severity=severity,
        flagged_spans=spans,
    )
