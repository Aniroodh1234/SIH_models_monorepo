# SwarajDesk AI Report Generator

A production-ready, advanced **RAG-powered (Retrieval-Augmented Generation)** backend system that analyzes civic complaint data and NGO survey reports to generate comprehensive, structured JSON reports using **Google Gemini 2.5 Pro** as the intelligence backbone.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Endpoints](#endpoints)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Building the Vector Store](#building-the-vector-store)
- [Running the Server](#running-the-server)
- [API Usage](#api-usage)
- [RAG Pipeline Details](#rag-pipeline-details)
- [Configuration](#configuration)

---

## Overview

SwarajDesk AI Report Generator powers the following API endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/survey-report` | `POST` | Generates 3 JSON reports (Survey + Backend + Fusion) for a specific civic category |
| `/survey-report/stream` | `POST` | Streaming SSE version of `/survey-report` with real-time progress and token chunks |

The system ingests two datasets:
- **Survey/NGO Data** (`dataset_fixed.json`) — Field research and NGO reports on civic issues
- **SwarajDesk Backend Complaints** (`swarajdesk_backend_complaints_3000.json`) — 3,000 real citizen complaints across 13 categories

---

## Architecture

```
Request
   │
   ▼
FastAPI (main.py)
   │
   ├── POST /survey-report ─────────────────────────────────────┐
   │       │                                                      │
   │   SurveyReportPipeline (Phase 1) ◄── survey_collection     │
   │   BackendReportPipeline (Phase 2) ◄── backend_collection   │
   │   FusionReportPipeline (Phase 3)  ◄── Reports 1 + 2        │
   │                                                              │
   └── POST /survey-report/stream ───── (SSE streaming version) ┘
```

---

## Project Structure

```
5_Report_Generator/
│
├── main.py                          # FastAPI app entry point
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (API keys)
│
├── config/
│   ├── settings.py                  # Central config (paths, model names, params)
│   └── vector_db_config.py          # ChromaDB dual-collection setup
│
├── app/
│   ├── dependencies.py              # Singleton pipeline injection
│   ├── routes/
│   │   └── survey_report.py         # POST /survey-report + /survey-report/stream
│   └── schemas/
│       ├── request_schemas.py       # Pydantic request models
│       └── response_schema.py       # Pydantic response models
│
├── pipelines/
│   ├── survey_pipeline.py           # Orchestrates Survey Report (Report 1)
│   ├── backend_pipeline.py          # Orchestrates Backend Report (Report 2)
│   └── fusion_pipeline.py           # Orchestrates Fusion Report (Report 3)
│
├── services/
│   ├── retriever/
│   │   ├── vector_retriever.py      # MMR + similarity retrieval from ChromaDB
│   │   └── hybrid_retriever.py      # Category-aware hybrid retrieval
│   ├── reranker/
│   │   └── reranker.py              # Cross-encoder reranking (ms-marco)
│   ├── processor/
│   │   ├── clusterer.py             # Groups docs by category into context
│   │   ├── duplicator.py            # Content-based deduplication
│   │   └── severity_tagger.py       # Tags documents by urgency level
│   └── report_generator/
│       ├── survey_report_generator.py    # LLM call for Report 1
│       ├── backend_report_generator.py   # LLM call for Report 2
│       └── fusion_report_generator.py    # LLM call for Report 3
│
├── models/
│   └── llm/
│       ├── llm_loader.py            # GeminiLLM wrapper (generate_json, expand_query, streaming)
│       └── prompt_template.py       # All 3 LLM prompt templates
│
├── utils/
│   ├── constants.py                 # VALID_CATEGORIES, CATEGORY_MAP (13 categories)
│   ├── validator.py                 # Category fuzzy-match resolution
│   ├── logger.py                    # Loguru structured logging
│   └── json_parser.py               # Robust JSON extraction from LLM output
│
├── scripts/
│   └── build_embeddings.py          # One-time script to build ChromaDB vector store
│
└── data/
    ├── raw/
    │   ├── dataset_fixed.json                         # NGO/Survey dataset
    │   └── swarajdesk_backend_complaints_3000.json    # Backend complaints
    └── embeddings/                                    # ChromaDB persisted files (auto-generated)
```

---

## Endpoints

### 1. `POST /survey-report`

Generates **3 structured JSON reports** for a given civic category using dual-store RAG:

**Request Body:**
```json
{
  "category": "Health"
}
```

**Valid Categories:**
`Infrastructure`, `Water Supply & Sanitation`, `Health`, `Education`, `Environment`, `Electricity & Power`, `Municipal Services`, `Transportation`, `Police Services`, `Housing & Urban Development`, `Social Welfare`, `Public Grievances`, `Revenue`, `Agriculture`, `Fire & Emergency`, `Sports & Youth Affairs`, `Tourism & Culture`

**Response:**
```json
{
  "success": true,
  "category": "Health",
  "resolved_category": "Health",
  "survey_report": { ... },        // Report 1 — NGO/Survey analysis
  "backend_report": { ... },       // Report 2 — Complaint patterns
  "fusion_report": { ... },        // Report 3 — Combined strategic analysis
  "pipeline_metadata": {
    "total_time_seconds": 85.3,
    "phase_1_2_time_seconds": 60.1,
    "phase_3_time_seconds": 25.2
  }
}
```

---

---

## Streaming (Real-time) Responses

The project supports real-time streaming responses using Server-Sent Events (SSE). The streaming endpoint runs alongside the blocking endpoint so clients can opt-in to receive incremental progress updates and LLM token chunks as reports are generated.

Streaming endpoint:
- `POST /survey-report/stream` — Streaming version of `POST /survey-report` (SSE). Use `fetch()` in browsers or `curl -N` / `requests` in clients.

Key behavior:
- The streaming endpoint emits structured SSE events with an `event:` type and a JSON `data:` payload. Event types include: `pipeline_start`, `progress`, `token`, `phase_complete`, `complete`, and `error`.
- `token` events stream raw LLM text chunks as Gemini generates tokens; these are partial JSON text pieces which the client can append to reconstruct the report incrementally.
- `phase_complete` events contain the fully parsed JSON report for that phase (the server accumulates tokens and runs a robust JSON extractor before emitting this event).
- The existing non-streaming endpoint (`/survey-report`) remains unchanged.

Protocol (example wire):

```
event: progress
data: {"phase":"retrieval","message":"Retrieving documents...","elapsed_s":1.2}

event: token
data: {"report":"survey_report","chunk":"{\n  \"report_type\": \"survey_repor"}

event: token
data: {"report":"survey_report","chunk":"t\",\n  \"category\": \"Health\","}

event: phase_complete
data: {"phase":"survey_report","elapsed_s":62.0,"report":{...}}

event: complete
data: {"success":true,"total_time_seconds":143.2}
```

Implementation notes (developer-facing):
- `utils/sse_helpers.py`: helper functions `format_sse()` (formats SSE wire strings) and `sync_gen_to_async()` (runs blocking sync generators in a thread pool and bridges to an async generator).
- `models/llm/llm_loader.py`: `_stream_model` (GenerationConfig without `response_mime_type`) and `generate_json_stream(prompt)` which calls `generate_content(..., stream=True)` and yields token chunks.
- `services/report_generator/*_report_generator.py`: `generate_stream()` methods that yield raw token chunks and finally a `__RESULT__:<json>` sentinel; they reuse the same prompt logic as the blocking `generate()` methods.
- `pipelines/*_pipeline.py`: `run_stream()` async generators that emit `progress` events for retrieval/rerank/dedup steps and forward LLM `token` events; they emit a `phase_complete` event with the parsed report dict once the stream completes.
- `app/routes/survey_report.py`: `POST /survey-report/stream` route that returns `StreamingResponse(..., media_type='text/event-stream')` and sets headers to reduce proxy buffering (e.g., `X-Accel-Buffering: no`).

Important caveats & tips:
- `response_mime_type="application/json"` is incompatible with `stream=True` on the Gemini SDK — the streaming model intentionally omits `response_mime_type` and streams text tokens; the server then reconstructs and parses JSON using the existing `utils/json_parser.py` robust extractor.
- Gemini "thinking" model parts may include non-text/thought chunks; the streaming reader skips thought metadata and only emits text parts.
- The `POST /survey-report/stream` endpoint runs the survey, backend, and fusion phases sequentially (to avoid interleaving token streams); the original parallel non-streaming implementation is unchanged.
- When testing with `curl`, use `-N` to disable buffering. For proxies (nginx), set `proxy_buffering off` or `X-Accel-Buffering: no` header.

Client examples (quick):
- Browser `fetch()` (POST): use `fetch('/survey-report/stream', { method:'POST', body: JSON.stringify({category:'Health'}), headers: {'Content-Type': 'application/json'} })` and read `resp.body.getReader()` to stream bytes.
- Curl (terminal): `curl -N -X POST http://127.0.0.1:8000/survey-report/stream -H "Content-Type: application/json" -d '{"category":"Health"}'`

Testing and rollout:
- The streaming changes are available via the `/stream` endpoint to avoid breaking current clients.
- Verify SSE using `curl -N` and a browser test page that consumes a `fetch()` reader for POST.

---

### 3. `GET /health`

Returns system health and vector store record counts.

### 4. `GET /categories`

Returns all 17 valid categories supported by the system.

---

## Tech Stack

| Component | Technology |
|---|---|
| **API Framework** | FastAPI + Uvicorn |
| **LLM** | Google Gemini 2.5 Pro (`gemini-2.5-pro`) |
| **Embedding Model** | Google `gemini-embedding-001` |
| **Vector Store** | ChromaDB (dual-collection, persistent) |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **RAG Framework** | LangChain + LangChain-Chroma |
| **Logging** | Loguru (file + console) |
| **Data Validation** | Pydantic v2 |

---

## Prerequisites

- Python **3.10+**
- Anaconda or virtualenv
- A valid **Google Gemini API Key**
- At least **8 GB RAM** (16 GB recommended for embedding build)
- **D: drive** or sufficient disk space (~2 GB for embeddings)

---

## Setup & Installation

### Step 1 — Clone / Navigate to the project

```powershell
cd D:\GEN_AI_PROJECTS\5_Report_Generator
```

### Step 2 — Create and activate a virtual environment

```powershell
# Using Anaconda
conda create -n report_gen python=3.11
conda activate report_gen

# OR using venv
python -m venv venv
.\venv\Scripts\activate
```

### Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

Create a `.env` file in the project root with the following:

```env
# Required
GEMINI_API_KEY=your_google_gemini_api_key_here

# Optional overrides
MODEL_NAME=gemini-2.5-pro
EMBEDDING_MODEL=models/gemini-embedding-001
```

> Get your Gemini API key from: https://aistudio.google.com/app/apikey

---

## Building the Vector Store

> This is a **one-time setup step** that must be completed before running the server.

The script reads both JSON datasets, creates embeddings using Gemini's embedding model, and persists them into two ChromaDB collections:

```powershell
python scripts/build_embeddings.py
```

**What this creates:**
- `data/embeddings/survey_collection` — ~12,000 NGO/survey documents
- `data/embeddings/backend_collection` — ~6,500 SwarajDesk complaint documents

This process takes 15-30 minutes depending on your internet speed (Gemini API calls for embeddings).

> ✅ You only need to run this **once**. The vector stores persist on disk.

---

## Running the Server

Once the embeddings are built, start the FastAPI server:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The server will be available at:
- **API Base**: http://127.0.0.1:8000
- **Interactive Docs (Swagger)**: http://127.0.0.1:8000/docs
- **ReDoc Documentation**: http://127.0.0.1:8000/redoc

> TensorFlow deprecation warnings on startup are **expected and harmless** — they come from the sentence-transformers cross-encoder reranker dependencies.

---

## API Usage

### Using Swagger UI

Visit http://127.0.0.1:8000/docs and use the interactive interface to call either endpoint.

### Using cURL

```bash
# Health check
curl http://127.0.0.1:8000/health

# Survey Report (POST with body)
curl -X POST http://127.0.0.1:8000/survey-report \
  -H "Content-Type: application/json" \
  -d '{"category": "Water Supply & Sanitation"}'

# Streaming Survey Report (SSE)
curl -N -X POST http://127.0.0.1:8000/survey-report/stream \
  -H "Content-Type: application/json" \
  -d '{"category": "Health"}'
```

### Using Python requests

```python
import requests

# Survey Report
resp = requests.post(
    "http://127.0.0.1:8000/survey-report",
    json={"category": "Infrastructure"}
)
print(resp.json())
```

---

## RAG Pipeline Details

### `/survey-report` — Triple Pipeline

```
1. Category Resolve    → Fuzzy-match user input to one of 17 valid categories
2. Query Expansion     → LLM generates rich semantic query from keywords
3. MMR Retrieval       → Fetch top-20 diverse documents from ChromaDB
4. Deduplication       → Content fingerprint-based duplicate removal
5. Severity Tagging    → Tag each doc: high / medium / low urgency
6. Cross-Encoder Rerank→ ms-marco reranker selects top-10 most relevant
7. Context Clustering  → Group docs by category for structured LLM context
8. LLM Generation      → Gemini 2.5 Pro generates structured JSON report
```

Pipelines 1 (Survey) and 2 (Backend) run **in parallel** using `asyncio`. Fusion (Pipeline 3) runs after both complete.

---

---

## Configuration

All tunable parameters are in `config/settings.py`:

| Parameter | Default | Description |
|---|---|---|
| `LLM_MODEL_NAME` | `gemini-2.5-pro` | Gemini model for report generation |
| `LLM_TEMPERATURE` | `0.3` | Low temperature for factual output |
| `LLM_MAX_OUTPUT_TOKENS` | `8192` | Max tokens per report generation |
| `RETRIEVAL_TOP_K` | `20` | Documents retrieved per query |
| `RERANKER_TOP_K` | `10` | Documents kept after reranking |
| `MMR_FETCH_K` | `60` | Candidate pool for MMR diversity |
| `MMR_LAMBDA_MULT` | `0.7` | MMR balance: 0=diverse, 1=relevant |
| `CHROMA_PERSIST_DIR` | `data/embeddings` | Where ChromaDB stores vectors |

