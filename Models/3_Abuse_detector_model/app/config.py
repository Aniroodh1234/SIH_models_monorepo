import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Hugging Face
    HF_API_KEY: str = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")

    # [ACTIVE — Groq LLM]
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # [DISABLED — Gemini LLM]
    # GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

settings = Settings()
