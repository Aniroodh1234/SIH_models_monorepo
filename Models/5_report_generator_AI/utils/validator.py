from typing import Optional
from utils.constants import VALID_CATEGORIES, CATEGORY_MAP, get_all_keywords
from utils.logger import get_logger

log = get_logger("validator")


def resolve_category(user_input: str) -> Optional[str]:
    """
    Resolve user input to a valid category name.

    Supports:
    1. Exact match (case-insensitive)
    2. Partial match (substring)
    3. Fuzzy keyword-based matching

    Args:
        user_input: Raw category string from the user

    Returns:
        Resolved category name, or None if no match found.
    """
    if not user_input or not user_input.strip():
        return None

    query = user_input.strip()

    # ── Strategy 1: Exact match (case-insensitive) ────────────────
    for cat in VALID_CATEGORIES:
        if cat.lower() == query.lower():
            log.info(f"Category exact match: '{query}' → '{cat}'")
            return cat

    # ── Strategy 2: Substring match ───────────────────────────────
    query_lower = query.lower()
    for cat in VALID_CATEGORIES:
        if query_lower in cat.lower() or cat.lower() in query_lower:
            log.info(f"Category substring match: '{query}' → '{cat}'")
            return cat

    # ── Strategy 3: Keyword-based fuzzy match ─────────────────────
    keywords_map = get_all_keywords()
    query_tokens = set(query_lower.replace("_", " ").replace("-", " ").split())

    best_match = None
    best_score = 0

    for cat, keywords in keywords_map.items():
        keyword_set = set(k.lower() for k in keywords)
        overlap = len(query_tokens & keyword_set)

        # Also check if any token is a substring of a keyword or vice versa
        for qt in query_tokens:
            for kw in keyword_set:
                if qt in kw or kw in qt:
                    overlap += 0.5

        if overlap > best_score:
            best_score = overlap
            best_match = cat

    if best_match and best_score >= 1.0:
        log.info(
            f"Category fuzzy match: '{query}' → '{best_match}' "
            f"(score: {best_score})"
        )
        return best_match

    log.warning(f"No category match found for: '{query}'")
    return None


def validate_report_json(report: dict) -> list[str]:
    """
    Validate a generated report JSON against the expected schema.

    Returns a list of validation errors (empty if valid).
    """
    errors = []

    required_fields = [
        "report_type", "category", "generated_at", "summary",
        "key_findings",
    ]

    for field in required_fields:
        if field not in report:
            errors.append(f"Missing required field: '{field}'")

    # Validate report_type
    valid_types = {"survey_report", "backend_report", "fusion_report"}
    if "report_type" in report and report["report_type"] not in valid_types:
        errors.append(
            f"Invalid report_type: '{report['report_type']}'. "
            f"Must be one of {valid_types}"
        )

    # Validate key_findings structure
    if "key_findings" in report:
        if not isinstance(report["key_findings"], list):
            errors.append("'key_findings' must be a list")
        else:
            for i, finding in enumerate(report["key_findings"]):
                if not isinstance(finding, dict):
                    errors.append(f"key_findings[{i}] must be a dict")
                elif "finding" not in finding:
                    errors.append(
                        f"key_findings[{i}] missing 'finding' field"
                    )

    return errors
