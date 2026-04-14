import sys
import os
import gc

# ── Force all caches to D: drive (C: is full) ────────────────────
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_NO_CUDA_MEMORY_CACHING"] = "1"
os.environ["TEMP"] = "D:\\temp"
os.environ["TMP"] = "D:\\temp"
os.environ["HF_HOME"] = "D:\\hf_cache"
os.environ["TRANSFORMERS_CACHE"] = "D:\\hf_cache"
os.environ["TORCH_HOME"] = "D:\\torch_cache"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "D:\\hf_cache\\sentence_transformers"

# Fix Windows console encoding
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Block TensorFlow import (not needed, causes paging file crash) ─
# Instead of importing real TF, make it raise ImportError so
# transformers/sentence-transformers gracefully skip TF code paths.
import importlib.abc
import importlib.machinery

class _BlockTFImporter(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Meta-path finder that blocks tensorflow imports."""
    _BLOCKED = {"tensorflow", "tensorflow.python", "tf_keras", "keras"}
    
    def find_module(self, fullname, path=None):
        if fullname.split(".")[0] in self._BLOCKED:
            return self
        return None
    
    def load_module(self, fullname):
        raise ImportError(f"Blocked: {fullname}")

sys.meta_path.insert(0, _BlockTFImporter())

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import shutil
from langchain_core.documents import Document

from config.settings import (
    SURVEY_DATASET_PATH,
    BACKEND_DATASET_PATH,
    CHROMA_PERSIST_DIR,
    SURVEY_COLLECTION_NAME,
    BACKEND_COLLECTION_NAME,
)


def load_data(file_path):
    """Load JSON dataset."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    return data


def create_documents(data, dataset_type):
    """Create LangChain Documents from raw data."""
    documents = []
    for item in data:
        content = item.get("content", "").strip()
        if not content:
            continue

        metadata = {
            "id": item.get("id", ""),
            "category": item.get("category", ""),
            "source_type": item.get("source_type", ""),
            "dataset": dataset_type,
        }

        if dataset_type == "survey":
            metadata["source_url"] = item.get("source_url", "") or ""

        if dataset_type == "backend":
            respondent = item.get("respondent", {})
            location = respondent.get("location", {})
            metadata["survey_id"] = item.get("survey_id", "")
            metadata["state"] = location.get("state", "")
            metadata["district"] = location.get("district", "")
            metadata["city"] = location.get("city", "")
            metadata["respondent_age"] = respondent.get("ageRange", "")
            metadata["respondent_gender"] = respondent.get("gender", "")

        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def build_collection(documents, collection_name, embedding_fn, batch_size=100):
    """Build a ChromaDB collection in batches."""
    from langchain_chroma import Chroma

    vectordb = None
    total = (len(documents) + batch_size - 1) // batch_size

    for batch_num, i in enumerate(range(0, len(documents), batch_size), 1):
        batch = documents[i:i + batch_size]
        print(f"  Batch {batch_num}/{total} ({len(batch)} docs)...", end="", flush=True)

        if vectordb is None:
            vectordb = Chroma.from_documents(
                documents=batch,
                embedding=embedding_fn,
                persist_directory=CHROMA_PERSIST_DIR,
                collection_name=collection_name,
            )
        else:
            vectordb.add_documents(batch)

        print(" done")
        gc.collect()

    return vectordb


def main():
    print("=" * 60)
    print("Building Dual Vector Store Collections")
    print("=" * 60)

    # Clear existing
    if os.path.exists(CHROMA_PERSIST_DIR):
        print(f"\nClearing: {CHROMA_PERSIST_DIR}")
        shutil.rmtree(CHROMA_PERSIST_DIR)
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

    # Check datasets
    for label, path in [("Survey", SURVEY_DATASET_PATH), ("Backend", BACKEND_DATASET_PATH)]:
        if not os.path.exists(path):
            print(f"FAIL: {label} not found: {path}")
            sys.exit(1)
        print(f"  {label}: {path}")

    # Load embedding model ONCE
    print("\nLoading embedding model...")
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from config.settings import GEMINI_API_KEY
        os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
        embedding_fn = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001"
        )
        _ = embedding_fn.embed_query("test_query")
        print("Embedding model loaded and validated.\n")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAIL: Could not load embedding model - {e}")
        sys.exit(1)

    # Build survey collection
    print("--- Building survey_collection ---")
    survey_data = load_data(SURVEY_DATASET_PATH)
    print(f"  Records: {len(survey_data)}")
    survey_docs = create_documents(survey_data, "survey")
    print(f"  Documents: {len(survey_docs)}")
    del survey_data
    gc.collect()
    build_collection(survey_docs, SURVEY_COLLECTION_NAME, embedding_fn)
    del survey_docs
    gc.collect()

    # Build backend collection
    print("\n--- Building backend_collection ---")
    backend_data = load_data(BACKEND_DATASET_PATH)
    print(f"  Records: {len(backend_data)}")
    backend_docs = create_documents(backend_data, "backend")
    print(f"  Documents: {len(backend_docs)}")
    del backend_data
    gc.collect()
    build_collection(backend_docs, BACKEND_COLLECTION_NAME, embedding_fn)
    del backend_docs
    gc.collect()

    # Verify
    print("\n--- Verification ---")
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    for name in [SURVEY_COLLECTION_NAME, BACKEND_COLLECTION_NAME]:
        try:
            col = client.get_collection(name)
            print(f"  {name}: {col.count()} records")
        except Exception as e:
            print(f"  {name}: FAILED - {e}")

    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()