import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Project Paths ─────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"

# ── Dataset Paths ─────────────────────────────────────────────────
SURVEY_DATASET_PATH = str(RAW_DIR / "dataset_fixed.json")
BACKEND_DATASET_PATH = str(RAW_DIR / "swarajdesk_survey_flattened.json")

# ── API Keys ──────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")

# ── Model Config ──────────────────────────────────────────────────
# LLM_MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-pro")  # COMMENTED OUT — expensive paid model
LLM_MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")  # FREE TIER — dev evaluation
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

# ── Cross-Encoder Reranker ────────────────────────────────────────
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# ── Vector DB ─────────────────────────────────────────────────────
SURVEY_COLLECTION_NAME = "survey_collection"
BACKEND_COLLECTION_NAME = "backend_collection"
CHROMA_PERSIST_DIR = str(EMBEDDINGS_DIR)

# ── LLM Generation Settings ──────────────────────────────────────
LLM_TEMPERATURE = 0.3          # Low for factual report generation
# LLM_MAX_OUTPUT_TOKENS = 8192   # COMMENTED OUT — caused truncation on Fusion reports
LLM_MAX_OUTPUT_TOKENS = 65536  # Gemini 2.5 Flash supports up to 65K output tokens
LLM_TOP_P = 0.95
LLM_TOP_K = 40

# ── Retrieval Settings ────────────────────────────────────────────
RETRIEVAL_TOP_K = 20           # Docs to retrieve per collection
RERANKER_TOP_K = 10            # Docs after reranking
MMR_FETCH_K = 60               # MMR candidate pool
MMR_LAMBDA_MULT = 0.7          # MMR diversity control
