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

SwarajDesk AI Report Generator powers two independent API endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/survey-report` | `POST` | Generates 3 JSON reports (Survey + Backend + Fusion) for a specific civic category |
| `/analyze-report` | `GET` | Generates one overarching global analysis report across ALL complaint categories — no input needed |

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
   └── GET /analyze-report ──────────────────────────────────── ┘
           │
       AnalyzeReportPipeline
           │
           ├── Multi-Category Expansion (13 categories)
           ├── MMR Retrieval (Max Marginal Relevance)
           ├── Deduplication + Severity Tagging
           ├── Document Clustering
           └── Gemini 2.5 Pro JSON Synthesis
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
│   ├── vector_db_config.py          # ChromaDB dual-collection setup
│   └── llm_config.py                # LLM configuration helpers
│
├── app/
│   ├── dependencies.py              # Singleton pipeline injection
│   ├── routes/
│   │   ├── survey_report.py         # POST /survey-report route
│   │   └── analyze_report.py        # GET /analyze-report route
│   └── schemas/
│       ├── request_schemas.py       # Pydantic request models
│       └── response_schema.py       # Pydantic response models
│
├── pipelines/
│   ├── survey_pipeline.py           # Orchestrates Survey Report (Report 1)
│   ├── backend_pipeline.py          # Orchestrates Backend Report (Report 2)
│   ├── fusion_pipeline.py           # Orchestrates Fusion Report (Report 3)
│   └── analyze_pipeline.py          # Global MMR-based analyze pipeline
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
│       ├── fusion_report_generator.py    # LLM call for Report 3
│       └── analyze_report_generator.py   # LLM call for Global Report
│
├── models/
│   └── llm/
│       ├── llm_loader.py            # GeminiLLM wrapper (generate_json, expand_query)
│       └── prompt_template.py       # All 4 LLM prompt templates
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

### 2. `GET /analyze-report`

**No input required.** Automatically analyzes ALL complaints from the SwarajDesk backend dataset using multi-category MMR retrieval and generates one comprehensive global report.

**Request:**
```
GET /analyze-report
```
*(No body, no parameters — just call the endpoint)*

**Response:**
```json
{
  "report_type": "analyze_report",
  "category_scope": "All",
  "generated_at": "2026-04-12T...",
  "executive_summary": "...",
  "comprehensive_overview": "...",
  "total_sample_documents_analyzed": 35,
  "systemic_issues": [ ... ],
  "categorical_breakdown": [ ... ],
  "geographic_macro_analysis": { ... },
  "root_cause_analysis": [ ... ],
  "statistics_estimation": { ... },
  "strategic_recommendations": [ ... ],
  "pipeline_metadata": {
    "total_time_seconds": 190.4,
    "category_scope": "All",
    "retrieval_strategy": "Multi-Category MMR (Advanced RAG)"
  }
}
```

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

# Analyze Report (GET, no body needed)
curl http://127.0.0.1:8000/analyze-report
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

# Global Analyze Report (no input)
resp = requests.get("http://127.0.0.1:8000/analyze-report")
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

### `/analyze-report` — Advanced Multi-Category MMR

```
1. Iterate 13 categories → For each, LLM generates a targeted semantic query
2. MMR per category      → Fetch 15 diverse docs per category (~195 total fetched)
3. Global Deduplication  → Reduces to ~35 uniquely varied complaint samples
4. Severity Tagging      → Tags all unique docs
5. Context Clustering    → Organizes by all 13 category keys for rich context
6. Gemini Synthesis      → Generates overarching systemic-level global JSON report
```

This Advanced RAG strategy ensures:
- Full **dataset coverage** across all categories
- **Zero token waste** — only ~35 optimally diverse docs sent to LLM
- **High accuracy** — MMR prevents redundancy biases
- **Cost-effective** — Minimal Gemini API calls for maximum insight

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

