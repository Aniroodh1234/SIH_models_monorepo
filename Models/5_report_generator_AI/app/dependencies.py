from functools import lru_cache

from langchain_chroma import Chroma

from config.vector_db_config import (
    get_embedding_function,
    get_survey_store,
    get_backend_store,
)
from models.llm.llm_loader import GeminiLLM, get_llm
from pipelines.survey_pipeline import SurveyReportPipeline
from pipelines.backend_pipeline import BackendReportPipeline
from pipelines.fusion_pipeline import FusionReportPipeline
from utils.logger import get_logger

log = get_logger("dependencies")


_embedding_fn = None
_survey_store = None
_backend_store = None
_survey_pipeline = None
_backend_pipeline = None
_fusion_pipeline = None


def get_embedding_fn():
    """Get or create the shared embedding function."""
    global _embedding_fn
    if _embedding_fn is None:
        log.info("Initializing embedding function...")
        _embedding_fn = get_embedding_function()
    return _embedding_fn


def get_survey_vector_store() -> Chroma:
    """Get or create the survey vector store."""
    global _survey_store
    if _survey_store is None:
        _survey_store = get_survey_store(get_embedding_fn())
    return _survey_store


def get_backend_vector_store() -> Chroma:
    """Get or create the backend vector store."""
    global _backend_store
    if _backend_store is None:
        _backend_store = get_backend_store(get_embedding_fn())
    return _backend_store


def get_survey_pipeline() -> SurveyReportPipeline:
    """Get or create the survey pipeline."""
    global _survey_pipeline
    if _survey_pipeline is None:
        llm = get_llm()
        store = get_survey_vector_store()
        _survey_pipeline = SurveyReportPipeline(llm, store)
        log.info("Survey pipeline initialized")
    return _survey_pipeline


def get_backend_pipeline() -> BackendReportPipeline:
    """Get or create the backend pipeline."""
    global _backend_pipeline
    if _backend_pipeline is None:
        llm = get_llm()
        store = get_backend_vector_store()
        _backend_pipeline = BackendReportPipeline(llm, store)
        log.info("Backend pipeline initialized")
    return _backend_pipeline


def get_fusion_pipeline() -> FusionReportPipeline:
    """Get or create the fusion pipeline."""
    global _fusion_pipeline
    if _fusion_pipeline is None:
        llm = get_llm()
        _fusion_pipeline = FusionReportPipeline(llm)
        log.info("Fusion pipeline initialized")
    return _fusion_pipeline
