"""
Gemini LLM Loader — wraps Google Generative AI for structured JSON report generation.

Provides:
  - GeminiLLM   : Main LLM wrapper with generate_json() and expand_query()
  - get_llm()   : Singleton factory (lazy-initialized)
"""

import os
import time
from typing import Optional

import google.generativeai as genai

from config.settings import (
    GEMINI_API_KEY,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_TOP_P,
    LLM_TOP_K,
)
from utils.json_parser import extract_json
from utils.logger import get_logger

log = get_logger("llm_loader")

# ── Singleton instance ────────────────────────────────────────────
_llm_instance: Optional["GeminiLLM"] = None


class GeminiLLM:
    """
    Wrapper around Google Gemini for structured JSON report generation.

    Key methods:
      generate_json(prompt) → dict
      expand_query(category, keywords) → str
    """

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Please add it to your .env file."
            )

        log.info(f"Initializing Gemini LLM: {LLM_MODEL_NAME}")
        os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
        genai.configure(api_key=GEMINI_API_KEY)

        self.model_name = LLM_MODEL_NAME

        # JSON generation config — forces pure JSON output (no code fences)
        self._json_generation_config = genai.types.GenerationConfig(
            temperature=LLM_TEMPERATURE,
            max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
            top_p=LLM_TOP_P,
            top_k=LLM_TOP_K,
            response_mime_type="application/json",
        )

        # Text generation config — for query expansion (plain text)
        self._text_generation_config = genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=200,
        )

        # Safety settings — prevent SAFETY blocks on benign civic data
        self._safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        # Model for JSON report generation
        self._model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self._json_generation_config,
            safety_settings=self._safety_settings,
        )

        # Model for text query expansion
        self._text_model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self._text_generation_config,
            safety_settings=self._safety_settings,
        )

        log.info(
            f"Gemini LLM ready: model={self.model_name}, "
            f"temp={LLM_TEMPERATURE}, max_tokens={LLM_MAX_OUTPUT_TOKENS}, "
            f"response_mime_type=application/json"
        )

    def generate_json(
        self,
        prompt: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> dict:
        """
        Send a prompt to Gemini and parse the JSON response.

        Args:
            prompt: Full prompt string (should instruct LLM to return JSON)
            max_retries: Number of retry attempts on failure
            retry_delay: Seconds between retries

        Returns:
            Parsed JSON as dict, or empty dict on failure
        """
        for attempt in range(1, max_retries + 1):
            try:
                log.info(
                    f"Generating JSON report "
                    f"(attempt {attempt}/{max_retries})..."
                )

                response = self._model.generate_content(prompt)

                # Extract text from response (handles thinking model)
                raw_text = self._extract_response_text(response)

                if not raw_text:
                    log.warning(f"Empty response from Gemini (attempt {attempt})")
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    continue

                log.debug(
                    f"Raw LLM response length: {len(raw_text)} chars"
                )

                # Parse JSON from response
                # With response_mime_type="application/json", the response
                # should be pure JSON, but we still use extract_json for safety
                result = extract_json(raw_text)

                if result is None:
                    log.warning(
                        f"Could not parse JSON from response "
                        f"(attempt {attempt}). "
                        f"Response preview: {raw_text[:200]}"
                    )
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    continue

                if not isinstance(result, dict):
                    log.warning(
                        f"Parsed result is not a dict "
                        f"(got {type(result).__name__})"
                    )
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    continue

                log.info(
                    f"JSON report generated successfully "
                    f"({len(result)} top-level keys)"
                )
                return result

            except Exception as e:
                log.error(
                    f"Gemini API error (attempt {attempt}/{max_retries}): {e}"
                )
                if attempt < max_retries:
                    time.sleep(retry_delay * attempt)  # Exponential backoff
                else:
                    log.error(
                        f"All {max_retries} attempts failed. "
                        f"Returning empty dict."
                    )

        return {}

    def _extract_response_text(self, response) -> str:
        """
        Extract text from a Gemini response, handling thinking models.

        For Gemini 2.5 thinking models, the response may contain
        both 'thought' parts and regular text parts. We skip
        thought parts and concatenate only the text parts.

        Returns:
            The extracted text, or empty string if no text is available.
        """
        try:
            # Quick path: response.text works for most cases
            if response and response.text:
                return response.text
        except (ValueError, AttributeError):
            pass

        # Fallback: extract from parts manually (thinking model)
        try:
            if response and response.candidates:
                parts = response.candidates[0].content.parts
                text_parts = []
                for part in parts:
                    thought = getattr(part, 'thought', False)
                    if not thought and hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    return "\n".join(text_parts)
        except Exception as e:
            log.warning(f"Failed to extract response parts: {e}")

        return ""

    def expand_query(self, category: str, keywords: list) -> str:
        """
        Expand a category into a rich semantic search query.

        Uses the LLM to generate an expanded query that captures the
        semantic space of the category for better retrieval recall.

        Args:
            category: User-facing category name
            keywords: Seed keywords for the category

        Returns:
            Expanded query string for vector search
        """
        kw_str = ", ".join(keywords) if keywords else category

        prompt = (
            f"Generate a comprehensive semantic search query (1-2 sentences) "
            f"for retrieving documents about civic complaints and issues "
            f"related to the category: '{category}'.\n\n"
            f"Seed keywords: {kw_str}\n\n"
            f"The query should:\n"
            f"- Cover the main sub-topics and issues of this category\n"
            f"- Use Natural Language that matches complaint descriptions\n"
            f"- Be specific enough to retrieve relevant documents\n"
            f"- Include both formal terms and common-person language\n\n"
            f"Return ONLY the query text, no explanation."
        )

        try:
            response = self._text_model.generate_content(prompt)

            text = self._extract_response_text(response)
            if text:
                expanded = text.strip()
                log.info(
                    f"Query expanded for '{category}': "
                    f"{expanded[:80]}..."
                )
                return expanded

        except Exception as e:
            log.warning(f"Query expansion failed: {e}. Using fallback.")

        # Fallback: simple keyword join
        fallback = f"{category} {' '.join(keywords)}"
        log.info(f"Using fallback query: {fallback}")
        return fallback

    def __repr__(self) -> str:
        return f"GeminiLLM(model={self.model_name})"


# ── Singleton Factory ─────────────────────────────────────────────

def get_llm() -> GeminiLLM:
    """
    Get or initialize the shared GeminiLLM instance (singleton).

    Returns:
        GeminiLLM instance
    """
    global _llm_instance
    if _llm_instance is None:
        log.info("Creating GeminiLLM singleton instance...")
        _llm_instance = GeminiLLM()
    return _llm_instance
