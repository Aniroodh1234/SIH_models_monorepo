"""
Groq LLM Loader — wraps Groq for structured JSON report generation.
"""

import os
import time
from typing import Optional
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from config.settings import (
    LLM_TEMPERATURE,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_TOP_P,
)
from utils.json_parser import extract_json
from utils.logger import get_logger

log = get_logger("llm_loader")

_llm_instance = None


class GroqLLM:
    def __init__(self):
        load_dotenv()
        # the user requested openai/gpt-oss-120b
        self.model_name = "openai/gpt-oss-120b"
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set.")

        log.info(f"Initializing Groq LLM: {self.model_name}")

        self._model = ChatGroq(
            model=self.model_name,
            groq_api_key=api_key,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_OUTPUT_TOKENS,
            model_kwargs={"top_p": LLM_TOP_P}
        )
        
        # text model (for queries)
        self._text_model = ChatGroq(
            model=self.model_name,
            groq_api_key=api_key,
            temperature=0.4,
            max_tokens=200,
        )

        log.info(f"Groq LLM ready: model={self.model_name}")

    def generate_json(
        self,
        prompt: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> dict:
        for attempt in range(1, max_retries + 1):
            try:
                log.info(f"Generating JSON report (attempt {attempt}/{max_retries})...")
                messages = [HumanMessage(content=prompt)]
                response = self._model.invoke(messages)
                raw_text = response.content

                if not raw_text:
                    log.warning(f"Empty response from Groq (attempt {attempt})")
                    if attempt < max_retries: time.sleep(retry_delay)
                    continue

                result = extract_json(raw_text)

                if result is None or not isinstance(result, dict):
                    log.warning(f"Could not parse JSON from response (attempt {attempt}).")
                    if attempt < max_retries: time.sleep(retry_delay)
                    continue

                log.info(f"JSON report generated successfully ({len(result)} top-level keys)")
                return result

            except Exception as e:
                log.error(f"Groq API error (attempt {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay * attempt)
                else:
                    log.error(f"All {max_retries} attempts failed. Returning empty dict.")

        return {}

    def generate_json_stream(self, prompt: str):
        streaming_instruction = (
            "IMPORTANT: Output ONLY raw JSON. Do NOT wrap the output in "
            "markdown code fences (```json or ```). Start directly with { "
            "and end with }. No extra text before or after the JSON.\n\n"
        )
        full_prompt = streaming_instruction + prompt

        log.info("Starting streaming JSON generation...")
        try:
            messages = [HumanMessage(content=full_prompt)]
            # Use the streaming interface of Langchain ChatGroq
            for chunk in self._model.stream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            log.error(f"Streaming generation error: {e}")
            raise
        log.info("Streaming JSON generation complete.")

    def expand_query(
        self,
        category: str,
        keywords: list,
        max_retries: int = 2,
    ) -> str:
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

        for attempt in range(1, max_retries + 1):
            try:
                messages = [HumanMessage(content=prompt)]
                response = self._text_model.invoke(messages)
                text = response.content

                if text:
                    expanded = text.strip()
                    log.info(f"Query expanded for '{category}': {expanded[:80]}...")
                    return expanded
                else:
                    log.warning(f"Query expansion returned empty response (attempt {attempt}/{max_retries})")

            except Exception as e:
                log.warning(f"Query expansion failed (attempt {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(1.0)

        fallback = f"{category} {' '.join(keywords)}"
        log.info(f"Using fallback query: {fallback}")
        return fallback

    def __repr__(self) -> str:
        return f"GroqLLM(model={self.model_name})"

# Alias for backward compatibility
GeminiLLM = GroqLLM

def get_llm() -> GroqLLM:
    global _llm_instance
    if _llm_instance is None:
        log.info("Creating GroqLLM singleton instance...")
        _llm_instance = GroqLLM()
    return _llm_instance
