# Advanced NLP System for Real-Time Abuse Detection and Content Sanitization

## Overview

This project implements an intelligent, multilingual text moderation system designed to sanitize user-submitted complaints on public grievance platforms. The system automatically identifies, extracts, and masks abusive or toxic expressions across English, Hindi, Hinglish, and Odia while preserving the semantic intent of the original message. Built using a hybrid AI approach, the system delivers high-precision abuse detection through the combined strengths of transformer-based toxicity scoring and large language model (LLM) phrase extraction.

## Key Features

- Multilingual Moderation: Detects and masks abusive content written in English, Hindi, Hinglish, and Odia.
- Phrase-Level Precision: Masks only harmful words or phrases without altering legitimate user input.
- Hybrid AI Engine: Uses Hugging Face Toxicity Model for scoring and Groq LLaMA-3.3 for structured phrase extraction.
- Context-Preserving Output: Sanitizes text while retaining original complaint structure for backend processing.
- Production-Ready API: Exposed as a RESTful FastAPI service optimized for real-time inference and integration with public service platforms.
- Scalable Deployment: Fully deployable on AWS EC2 with persistent process management.


## Project Architecture
```
AI-Abuse-Detector/
│
├── app/
│   ├── api/
│   │   └── moderation_route.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   ├── pipeline.py
│   │   ├── toxicity_api.py
│   │   └── llm_extractor.py
│   ├── config.py
│   └── utils/
│
├── main.py
├── requirements.txt
└── README.md
```

## Core Workflow

1. Text Preprocessing: User-submitted complaint text is normalized for consistent evaluation.
2. Toxicity Scoring: Hugging Face's toxicity classifier determines whether deeper analysis is required.
3. LLM-Based Phrase Extraction: Groq's LLaMA-3.3 model generates a structured JSON identifying abusive words or phrases.
4. Span Construction & Masking: Custom logic locates abusive terms in the text and masks them with placeholder tokens.
5. Final Response: Returns cleaned text, severity level, abuse indicators, and metadata for downstream systems.

## API Endpoint

**POST** `/api/v1/moderate`

Request Body:
```json
{
  "text": "hey u motherfucker tell me how to register"
}
```

Sample Response:
```json
{
  "has_abuse": true,
  "original_text": "hey u motherfucker tell me how to register",
  "clean_text": "hey u ****** tell me how to register",
  "severity": "high",
  "flagged_spans": [
    {
      "start": 6,
      "end": 19,
      "original": "motherfucker",
      "masked": "******",
      "lang": "en",
      "category": "abuse",
      "severity": "high",
      "confidence": 0.97
    }
  ]
}
```

## Environment Setup

### 1. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create `.env` file:
```
HF_API_KEY=your_huggingface_key
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
```

## Local Development

Run the FastAPI server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Open interactive API docs at:
```
http://localhost:8001/docs
```

## AWS EC2 Deployment Summary

1. Launch Ubuntu EC2 instance
2. Install Python, Git, and dependencies
3. Clone the repository
4. Configure `.env`
5. Start the API using Uvicorn
6. Run API persistently with PM2
7. (Optional) Configure NGINX reverse proxy for port 80 access

## Project Outcomes

- Ensures respectful communication on public grievance portals by removing abusive language without blocking user submissions.
- Maintains message integrity, enabling authorities to process complaints accurately.
- Enhances user experience by preventing rejection of complaints due to harmful language.
- Provides a scalable moderation backend suitable for civic-tech applications.
