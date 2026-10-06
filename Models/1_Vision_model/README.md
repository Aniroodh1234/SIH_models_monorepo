# Hybrid VLM–ViT AI System for Civic Issue Detection

## Overview

This project implements a highly scalable, production-grade AI system that automatically classifies civic issues from images across 20 government sectors. The system leverages a Hybrid VLM + ViT pipeline, enabling both broad semantic understanding and sector-specific validation for high accuracy and reliability. The API supports both direct image uploads and CDN image URLs, making it deployment-ready for modern digital governance platforms.

The solution is engineered for smart governance, enabling automated complaint triaging, proactive issue detection, and real-time decision support for municipal bodies.

## Key Features

- Hybrid Inference Engine: Combines a Vision-Language Model (Groq LLaMA) and fine-tuned ViT classifiers for robust validation.
- 20-Sector Hierarchical Classification: Extensive taxonomy covering civic infrastructure, education, environment, healthcare, safety, transportation, sanitation, and more.
- Two-Mode Input Pipeline: Accepts both local image uploads and external CDN image URLs.
- Model Safety Guardrails: ViT-based validation ensures reliability in critical sectors (Infrastructure, Education, Environment).
- Cloud-Native Architecture: Fully optimized for deployment on AWS EC2 with GPU/CPU fallback support.
- Production-Ready API: FastAPI-based inference service with CORS support and Swagger auto-documentation.
- Modular and Extensible Codebase: Easily adaptable for additional sectors, retraining, or custom integrations.

## Technology Stack

FastAPI, Groq LLaMA Vision Model, HuggingFace Transformers, Vision Transformer (ViT), PyTorch, Torchvision, Pillow, Requests, AWS EC2, Uvicorn, Python Dotenv

## Architecture Diagram (Conceptual)

**Input Layer:**

- User uploads image or provides a CDN link
- System normalizes into raw byte stream

**VLM Processing (Primary Brain):**

- Groq LLaMA VLM processes image
- Predicts sector + category from 20-sector taxonomy

**ViT Validation (Guard Layer):**

- ViT models validate predictions for Infrastructure, Education, and Environment
- Overrides incorrect or low-confidence classifications

**Decision Engine:**

- Hybrid logic determines final sector, category, and issue validity
- Generates structured JSON output

**API Response:**

- Provides high-confidence predictions with metadata

## Why a Hybrid VLM + ViT Pipeline?

### 1. Vision-Language Models

- VLMs excel at semantic comprehension, enabling broad contextual reasoning across all 20 sectors.
- They are ideal for general-purpose vision tasks but may occasionally hallucinate category labels.

### 2. Vision Transformer (ViT) Models

- ViTs provide fine-grained, domain-specific classification and deliver deterministic outputs.
- Sector-specific ViT guardrails significantly reduce false positives in critical civic categories.

### 3. Combined Benefit

The hybrid design delivers:

- High interpretability
- Increased fault tolerance
- Better precision and recall
- Lower misclassification rates

This alignment creates a reliable, production-ready model for public governance workflows.

## API Endpoints

### 1. Health Check

**GET** `/`

Returns API status and running mode.

### 2. Multi-Mode Prediction Endpoint

**POST** `/predict`

Supports both:

- `image` → File upload (multipart/form-data)
- `image_url` → CDN URL (multipart/form-data)

Example (File Upload):
```bash
curl -F "image=@pothole.jpg" http://<server-ip>:8000/predict
```

Example (CDN URL):
```bash
curl -F "image_url=https://example.com/image.jpg" http://<server-ip>:8000/predict
```

### 3. JSON-Based URL Prediction

**POST** `/predict-from-url`

Body:
```json
{
  "image_url": "https://example.com/image.jpg"
}
```

## Output Schema
```json
{
  "sector": "Infrastructure",
  "category": "potholes",
  "is_valid": true,
  "source": "vlm_primary_vit_guard",
  "confidence_vlm": 1.0,
  "confidence_vit": 0.92
}
```

## Project Structure
```
SwarajDesk_CV_Project/
│
├── Fastapi_app/
│   ├── main.py                  # API entry point
│   ├── inference.py             # Hybrid VLM + ViT pipeline
│   ├── utils.py                 # Image transforms & URL handlers
│   ├── models/                  # .pt ViT weights
│   └── venv/                    # Virtual environment
│
├── requirements.txt
└── README.md
```

## Deployment (AWS EC2)

### 1. Create Environment
```bash
sudo apt update && sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the API
```bash
uvicorn Fastapi_app.main:app --host 0.0.0.0 --port 8000
```

### 3. Open Security Group

Allow inbound traffic for:

- Port 8000 (API)
- Port 22 (SSH)

## Scalability & Reliability

This system is designed with enterprise-grade scalability in mind:

- Stateless microservice architecture
- Load-balancer friendly
- Supports model offloading & distributed inference
- Optimized for CPU-based and GPU-based deployment
- Lightweight ViT models for low-latency guardrail checks
