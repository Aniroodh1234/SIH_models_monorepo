"""
Embedding Model — builds dual ChromaDB collections from separate datasets.

Collection 1: survey_collection  → from dataset_fixed.json (NGO/survey data)
Collection 2: backend_collection → from swarajdesk_survey_flattened.json
"""

import os
import json
from typing import List, Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from tqdm import tqdm

from config.settings import (
    EMBEDDING_MODEL_NAME,
    CHROMA_PERSIST_DIR,
    SURVEY_COLLECTION_NAME,
    BACKEND_COLLECTION_NAME,
)
from utils.logger import get_logger

log = get_logger("embedding_model")


class EmbeddingModel:
    """
    Manages document creation and vector store building for both datasets.
    """

    def __init__(self):
        self.model_name = EMBEDDING_MODEL_NAME
        self.persist_directory = CHROMA_PERSIST_DIR
        self._embedding_function = None  # Lazy-loaded, cached

        os.makedirs(self.persist_directory, exist_ok=True)

        log.info(f"Embedding model: {self.model_name}")
        log.info(f"Persist directory: {self.persist_directory}")

    def _get_embedding_function(self) -> "GoogleGenerativeAIEmbeddings":
        """Initialize the embedding function (cached singleton)."""
        if self._embedding_function is None:
            log.info("Loading embedding model (first time)...")
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            from config.settings import GEMINI_API_KEY
            import os
            os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
            self._embedding_function = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001"
            )
            log.info("Embedding model loaded.")
        return self._embedding_function

    def load_dataset(self, file_path: str) -> List[dict]:
        """Load a JSON dataset from file."""
        log.info(f"Loading dataset: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle SwarajDesk structure: { "survey_definitions": [...], "records": [...] }
        if isinstance(data, dict) and "records" in data:
            data = data["records"]

        log.info(f"Loaded {len(data)} records")
        return data

    def create_survey_documents(self, data: List[dict]) -> List[Document]:
        """
        Create LangChain Documents from survey/NGO dataset.
        Preserves all metadata including source URLs.
        """
        documents = []

        for item in data:
            content = item.get("content", "").strip()
            if not content:
                continue

            metadata = {
                "id": item.get("id", ""),
                "category": item.get("category", ""),
                "source_type": item.get("source_type", ""),
                "source_url": item.get("source_url", "") or "",
                "created_at": item.get("created_at", ""),
                "dataset": "survey",
            }

            documents.append(
                Document(page_content=content, metadata=metadata)
            )

        return documents

    def create_backend_documents(self, data: List[dict]) -> List[Document]:
        """
        Create LangChain Documents from SwarajDesk backend dataset.
        Includes respondent demographic info in metadata.
        """
        documents = []

        for item in data:
            content = item.get("content", "").strip()
            if not content:
                continue

            respondent = item.get("respondent", {})
            location = respondent.get("location", {})

            metadata = {
                "id": item.get("id", ""),
                "category": item.get("category", ""),
                "source_type": item.get("source_type", "survey"),
                "survey_id": item.get("survey_id", ""),
                "survey_title": item.get("survey_title", ""),
                "respondent_age": respondent.get("ageRange", ""),
                "respondent_gender": respondent.get("gender", ""),
                "state": location.get("state", ""),
                "district": location.get("district", ""),
                "city": location.get("city", ""),
                "pin": location.get("pin", ""),
                "created_at": item.get("created_at", ""),
                "dataset": "backend",
            }

            documents.append(
                Document(page_content=content, metadata=metadata)
            )

        return documents

    def build_collection(
        self,
        documents: List[Document],
        collection_name: str,
        batch_size: int = 500,
    ) -> Chroma:
        """
        Build a ChromaDB collection from documents with batching.

        Args:
            documents: List of LangChain Documents
            collection_name: Name for the Chroma collection
            batch_size: Number of docs to add per batch

        Returns:
            Chroma vector store instance
        """
        log.info(
            f"Building collection '{collection_name}' "
            f"with {len(documents)} documents..."
        )

        embedding_function = self._get_embedding_function()

        # Build in batches to avoid memory issues
        vectordb = None
        total_batches = (len(documents) + batch_size - 1) // batch_size

        for i in tqdm(range(0, len(documents), batch_size),
                      desc=f"Building {collection_name}",
                      total=total_batches):
            batch = documents[i:i + batch_size]

            if vectordb is None:
                # First batch creates the collection
                vectordb = Chroma.from_documents(
                    documents=batch,
                    embedding=embedding_function,
                    persist_directory=self.persist_directory,
                    collection_name=collection_name,
                )
            else:
                vectordb.add_documents(batch)

        log.info(
            f"✅ Collection '{collection_name}' built: "
            f"{len(documents)} documents"
        )
        return vectordb

    def build_all(
        self,
        survey_path: str,
        backend_path: str,
    ) -> dict:
        """
        Build both vector store collections.

        Args:
            survey_path: Path to dataset_fixed.json
            backend_path: Path to swarajdesk_survey_flattened.json

        Returns:
            Dict with collection stats
        """
        # ── Load datasets ─────────────────────────────────────────
        survey_data = self.load_dataset(survey_path)
        backend_data = self.load_dataset(backend_path)

        # ── Create documents ──────────────────────────────────────
        log.info("Creating survey documents...")
        survey_docs = self.create_survey_documents(survey_data)
        log.info(f"Survey documents: {len(survey_docs)}")

        log.info("Creating backend documents...")
        backend_docs = self.create_backend_documents(backend_data)
        log.info(f"Backend documents: {len(backend_docs)}")

        # ── Build collections ─────────────────────────────────────
        survey_store = self.build_collection(
            survey_docs, SURVEY_COLLECTION_NAME
        )
        backend_store = self.build_collection(
            backend_docs, BACKEND_COLLECTION_NAME
        )

        stats = {
            SURVEY_COLLECTION_NAME: len(survey_docs),
            BACKEND_COLLECTION_NAME: len(backend_docs),
            "total": len(survey_docs) + len(backend_docs),
        }

        log.info(f"✅ All collections built: {stats}")
        return stats