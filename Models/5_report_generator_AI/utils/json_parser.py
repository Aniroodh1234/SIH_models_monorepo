import re
import json
from typing import Any, Optional

from utils.logger import get_logger

log = get_logger("json_parser")


def extract_json(text: str) -> Optional[dict | list]:
    """
    Extract JSON from LLM response text using multiple strategies.

    Args:
        text: Raw LLM response string

    Returns:
        Parsed JSON object (dict or list), or None if all strategies fail.
    """
    if not text or not text.strip():
        log.warning("Empty text provided to JSON parser")
        return None

    strategies = [
        ("direct_parse", _try_direct_parse),
        ("code_fence_extraction", _try_code_fence),
        ("brace_extraction", _try_brace_extraction),
        ("relaxed_parse", _try_relaxed_parse),
        ("truncated_repair", _try_truncated_repair),
    ]

    for name, strategy in strategies:
        try:
            result = strategy(text)
            if result is not None:
                log.debug(f"JSON extracted via strategy: {name}")
                return result
        except Exception as e:
            log.debug(f"Strategy '{name}' failed: {e}")
            continue

    log.error("All JSON extraction strategies failed")
    return None


def safe_extract_json(text: str, default: Any = None) -> Any:
    """
    Like extract_json but returns a default value instead of None on failure.
    """
    result = extract_json(text)
    return result if result is not None else (default or {})


def _try_direct_parse(text: str) -> Optional[dict | list]:
    """Strategy 1: Direct JSON parse."""
    stripped = text.strip()
    return json.loads(stripped)


def _try_code_fence(text: str) -> Optional[dict | list]:
    """Strategy 2: Extract from markdown code fences."""
    # Match ```json ... ``` or ``` ... ```
    patterns = [
        r"```json\s*\n?(.*?)\n?\s*```",
        r"```\s*\n?(.*?)\n?\s*```",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            content = _fix_common_issues(content)
            return json.loads(content)

    return None


def _try_brace_extraction(text: str) -> Optional[dict | list]:
    """Strategy 3: Find the outermost JSON object or array."""
    # Find first { or [
    obj_start = text.find("{")
    arr_start = text.find("[")

    if obj_start == -1 and arr_start == -1:
        return None

    # Determine which comes first
    if obj_start == -1:
        start = arr_start
        open_char, close_char = "[", "]"
    elif arr_start == -1:
        start = obj_start
        open_char, close_char = "{", "}"
    else:
        if obj_start < arr_start:
            start = obj_start
            open_char, close_char = "{", "}"
        else:
            start = arr_start
            open_char, close_char = "[", "]"

    # Find matching close
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                candidate = _fix_common_issues(candidate)
                return json.loads(candidate)

    return None


def _try_relaxed_parse(text: str) -> Optional[dict | list]:
    """Strategy 4: Fix common JSON issues then parse."""
    # Try to find JSON-like content
    for line_text in [text, text.strip()]:
        fixed = _fix_common_issues(line_text)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            continue

    return None


def _fix_common_issues(text: str) -> str:
    """Fix common JSON formatting issues from LLM output."""
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Remove single-line comments (// ...)
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)

    # Remove non-printable control characters (except \n, \r, \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    # Escape raw control characters inside JSON string values.
    # json.loads() rejects raw \n, \r, \t inside strings unless escaped.
    text = _escape_control_chars_in_strings(text)

    return text


def _escape_control_chars_in_strings(text: str) -> str:
    """
    Escape raw control characters (newline, tab, CR) that appear inside
    JSON string values.  Characters outside strings are left untouched
    so the structural formatting (pretty-printed JSON) is preserved.
    """
    result = []
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue

        if ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue

        # Only escape control chars when we're inside a JSON string value
        if in_string:
            if ch == '\n':
                result.append('\\n')
                continue
            elif ch == '\r':
                result.append('\\r')
                continue
            elif ch == '\t':
                result.append('\\t')
                continue

        result.append(ch)

    return ''.join(result)


def _try_truncated_repair(text: str) -> Optional[dict | list]:
    """
    Strategy 5: Repair truncated JSON from LLM output that was cut off
    due to max_output_tokens limit.

    When the model hits the token limit, the JSON output is truncated
    mid-string or mid-object. This strategy:
    1. Finds the start of the JSON
    2. Closes any open string
    3. Closes all open arrays and objects in the correct order
    4. Parses the repaired JSON
    """
    # Find the first { or [
    start = -1
    for i, ch in enumerate(text):
        if ch in ('{', '['):
            start = i
            break

    if start == -1:
        return None

    json_text = text[start:]
    json_text = _fix_common_issues(json_text)

    # Track state: are we inside a string? what brackets are open?
    in_string = False
    escape_next = False
    stack = []  # stack of open brackets: '{' or '['

    for ch in json_text:
        if escape_next:
            escape_next = False
            continue

        if ch == '\\' and in_string:
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == '{':
            stack.append('{')
        elif ch == '[':
            stack.append('[')
        elif ch == '}':
            if stack and stack[-1] == '{':
                stack.pop()
        elif ch == ']':
            if stack and stack[-1] == '[':
                stack.pop()

    if not stack:
        # JSON is already balanced — this strategy won't help
        return None

    # The JSON is truncated. Repair it:
    repaired = json_text

    # If we're inside an open string, close it
    if in_string:
        repaired += '"'

    # Remove any trailing partial key-value (e.g., "key": "partial)
    # by trimming back to the last complete value
    repaired = re.sub(r',\s*"[^"]*"\s*:\s*$', '', repaired)
    repaired = re.sub(r',\s*$', '', repaired)

    # Close all open brackets in reverse order
    for bracket in reversed(stack):
        if bracket == '{':
            repaired += '}'
        elif bracket == '[':
            repaired += ']'

    # Final cleanup: remove trailing commas before closing brackets
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

    try:
        result = json.loads(repaired)
        log.warning(
            f"Repaired truncated JSON: closed {len(stack)} open bracket(s). "
            f"Some data at the end may be incomplete."
        )
        return result
    except json.JSONDecodeError:
        return None
