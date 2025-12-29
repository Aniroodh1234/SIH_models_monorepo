import json
from typing import List, Dict, Any
import httpx

from app.config import settings
from app.models.schemas import FlaggedSpan

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


SYSTEM_PROMPT = """
You are a strict content moderation engine for a citizen complaint system.
Your ONLY job is to find abusive, profane, disrespectful, or slur words/phrases
in the given text. The text may contain English, Hindi, Hinglish (Roman Hindi),
and Odia (possibly in Latin script).

Rules:
- Do NOT rewrite or paraphrase the sentence.
- Do NOT censor normal frustration or criticism if there is no abusive word.
- Only focus on clear bad words, cuss words, slurs, strong insults, and similar.
- If there is no abusive or disrespectful word, return an empty list.

You MUST answer ONLY with a single JSON object with this exact structure:

{
  "abusive_phrases": [
    {
      "phrase": "exact bad word or short phrase as it appears in text",
      "lang": "en|hi|hinglish|odia|unknown",
      "category": "abuse|slur|sexual|threat|obscene|other",
      "severity": "low|medium|high"
    }
  ]
}

If there are no abusive words, use:
{ "abusive_phrases": [] }
"""


async def call_groq_llm_for_phrases(text: str) -> Dict[str, Any]:
    """
    Calls Groq llama-3.3-70b-versatile to get abusive phrases in the given text.
    Returns parsed JSON dict: { "abusive_phrases": [...] }
    On any error, returns { "abusive_phrases": [] }.
    """
    if not settings.GROQ_API_KEY:
        # No key configured, fail gracefully
        return {"abusive_phrases": []}

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(GROQ_URL, headers=headers, json=payload)

    data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        print("Could not extract 'content' field from Groq response:", e)
        return {"abusive_phrases": []}

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        print("Groq did not return valid JSON format")
        return {"abusive_phrases": []}
    
        # If parsed is not a dict, fall back to empty result
    if not isinstance(parsed, dict):
        return {"abusive_phrases": []}

    # If missing abusive_phrases key, also fall back
    if "abusive_phrases" not in parsed or not isinstance(parsed["abusive_phrases"], list):
        return {"abusive_phrases": []}

    # Final return (always a dict — never None)
    return parsed or {"abusive_phrases": []}


def build_spans_from_phrases(text: str, parsed: Dict[str, Any]) -> List[FlaggedSpan]:
    """
    Convert LLM output { "abusive_phrases": [...] } into a list of FlaggedSpan.
    We do NOT trust the LLM with indices; instead we:
      - Take each 'phrase'
      - Find all (non-overlapping) occurrences in the text
      - Create spans for each occurrence.
    """
    spans: List[FlaggedSpan] = []
    abusive_list = parsed.get("abusive_phrases", [])

    for item in abusive_list:
        phrase = item.get("phrase", "")
        if not phrase:
            continue

        lang = item.get("lang")
        category = item.get("category")
        severity = item.get("severity")

        # Find all non-overlapping occurrences of phrase in text
        search_from = 0
        while True:
            idx = text.lower().find(phrase.lower(), search_from)
            if idx == -1:
                break

            start = idx
            end = idx + len(phrase)

            spans.append(
                FlaggedSpan(
                    start=start,
                    end=end,
                    original=text[start:end],
                    masked="******",
                    lang=lang,
                    category=category,
                    severity=severity,
                    confidence=None,  # we don't get numeric score here
                )
            )

            search_from = end  # continue search after this span

    return spans
