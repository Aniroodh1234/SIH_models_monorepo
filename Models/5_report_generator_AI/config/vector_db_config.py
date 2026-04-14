import chromadb
from langchain_chroma import Chroma

from config.settings import (
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL_NAME,
    SURVEY_COLLECTION_NAME,
    BACKEND_COLLECTION_NAME,
)
from utils.logger import get_logger

log = get_logger("vector_db_config")


def get_embedding_function() -> "GoogleGenerativeAIEmbeddings":
    """
    Initialize the Google Generative AI embedding function.
    """
    log.info(f"Loading embedding model: gemini-embedding-001")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from config.settings import GEMINI_API_KEY
    import os
    import warnings

    # Suppress the noisy API key warning from langchain-google-genai
    warnings.filterwarnings("ignore", message="Both GOOGLE_API_KEY and GEMINI_API_KEY are set.*")

    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001"
    )

def get_vector_store(
    collection_name: str,
    embedding_function: "GoogleGenerativeAIEmbeddings" = None,
) -> Chroma:
    """
    Get a LangChain Chroma vector store for a specific collection.

    Args:
        collection_name: Either SURVEY_COLLECTION_NAME or BACKEND_COLLECTION_NAME
        embedding_function: Optional pre-loaded embedding function

    Returns:
        LangChain Chroma vector store instance
    """
    if embedding_function is None:
        embedding_function = get_embedding_function()

    log.info(
        f"Loading vector store: collection='{collection_name}', "
        f"path='{CHROMA_PERSIST_DIR}'"
    )

    return Chroma(
        collection_name=collection_name,
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embedding_function,
    )


def get_survey_store(
    embedding_function: "GoogleGenerativeAIEmbeddings" = None,
) -> Chroma:
    """Get the survey/NGO vector store."""
    return get_vector_store(SURVEY_COLLECTION_NAME, embedding_function)


def get_backend_store(
    embedding_function: "GoogleGenerativeAIEmbeddings" = None,
) -> Chroma:
    """Get the SwarajDesk backend vector store."""
    return get_vector_store(BACKEND_COLLECTION_NAME, embedding_function)


def verify_collections() -> dict:
    """
    Verify both collections exist and return record counts.
    """
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    result = {}
    for name in [SURVEY_COLLECTION_NAME, BACKEND_COLLECTION_NAME]:
        try:
            col = client.get_collection(name)
            count = col.count()
            result[name] = {"exists": True, "count": count}
            log.info(f"Collection '{name}': {count} records")
        except Exception as e:
            result[name] = {"exists": False, "error": str(e)}
            log.warning(f"Collection '{name}' not found: {e}")

    return result
