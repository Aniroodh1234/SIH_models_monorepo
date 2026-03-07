# Hybrid Complaint Categorization Model

## Overview

**CiviResolve** is a compounded AI-powered civic complaint intelligence model designed for automated classification of citizen grievances in digital governance systems. The model is built as part of the **SwarajDesk Citizen Grievance Redressal Platform**, where citizens can submit complaints through web portals, chatbots, or other interfaces.

The system combines **traditional machine learning and large language models** to analyze complaint text, determine the relevant government sector, and identify the precise issue type. The objective is to automate complaint routing and enable **accurate form auto-filling for government grievance systems**, reducing manual intervention and improving response efficiency.

CiviResolve is designed to support **multilingual complaints**, structured taxonomy classification, and robust handling of ambiguous or noisy inputs. By combining a locally trained classifier with an advanced reasoning model, the system ensures both **speed and accuracy** in complaint categorization.

---

## Key Features

* **Multilingual Complaint Processing**
  Citizens can submit complaints in different languages. The system automatically translates them into English before classification.

* **Compounded AI Architecture**
  Combines a trained **DistilBERT classification model** with a **Large Language Model (LLM)** for refined reasoning and taxonomy-based categorization.

* **Structured Civic Taxonomy**
  Uses predefined government sectors and issue types to prevent hallucinated outputs and maintain standardized complaint classification.

* **High-Confidence Filtering**
  If the DistilBERT model predicts a category with high confidence, the result is accepted directly. Otherwise, the LLM performs deeper reasoning.

* **Automatic Form Assistance**
  The final output includes both **sector and issue type**, enabling automated form filling and routing to appropriate departments.

* **FastAPI Integration**
  The model is deployed as a REST API using FastAPI for seamless integration with web or mobile platforms.

* **Robust Error Handling**
  Invalid or abusive complaints are detected and returned as `"not_recognized"`.

---

## Architecture

The CiviResolve model follows a compounded AI architecture that integrates multiple processing stages.

```
Citizen Complaint
        │
        ▼
Language Detection & Translation
        │
        ▼
DistilBERT Complaint Classifier
        │
        ├── High Confidence → Return Prediction
        │
        ▼
Large Language Model (Groq OSS-120B)
        │
        ▼
Taxonomy-Based Issue Identification
        │
        ▼
Final Structured Output
```

### Components

**1. Multilingual Processing**
Complaints are translated into English using a language utility module to ensure consistent classification.

**2. DistilBERT Classifier**
A lightweight transformer model trained on a custom civic complaint dataset.
It predicts the **broad government sector**.

**3. Confidence Evaluation**
If the model confidence exceeds a threshold (default: `0.65`), the prediction is accepted.

**4. LLM Reasoning Layer**
If confidence is low, a Groq-hosted LLM analyzes the complaint and selects the correct category and issue type from a constrained taxonomy.

**5. Structured Output Generator**
The system produces a JSON response that can be directly used by downstream automation systems.

---

## Civic Taxonomy Structure

CiviResolve uses a predefined taxonomy of civic sectors and issue types to prevent hallucination and ensure consistent classification.

### Example Categories

* Infrastructure
* Electricity and Power
* Water Supply and Sanitation
* Municipal Services
* Transportation
* Environment
* Health
* Education
* Housing and Urban Development
* Public Safety

### Example Issue Types

* potholes
* damaged_roads
* broken_streetlight
* water_pipeline_leak
* garbage_overflow
* broken_school_gate
* air_pollution
* illegal_construction

The taxonomy can be extended easily as new complaint categories emerge.

---

## Model Training

The DistilBERT model was trained using a structured complaint dataset in **JSONL format**. Each record contains a complaint text and a labeled category.

Example dataset entry:

```json
{
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "pothole on main road needs fixing"}]
    },
    {
      "role": "model",
      "parts": [{"text": "infrastructure"}]
    }
  ]
}
```

Training was performed using **HuggingFace Transformers** with the following configuration:

* Base Model: `distilbert-base-uncased`
* Training Platform: Google Colab
* Framework: PyTorch
* Training Epochs: 5
* Max Token Length: 128
* Optimizer: AdamW
* Learning Rate: 2e-5

After training, the model weights were exported as:

```
distilbert_complaint_model.pt
label_map.json
```

---

## Installation

### 1. Clone the repository

```
git clone <repository-url>
cd Auto-categorization_AI
```

### 2. Create a virtual environment

```
python -m venv ai_category
ai_category\Scripts\activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

---

## Project Structure

```
Auto-categorization_AI
│
├── app
│   ├── api
│   │   └── predict.py
│   │
│   ├── services
│   │   ├── classifier_service.py
│   │   └── llm_services.py
│   │
│   ├── models
│   │   ├── distilbert_complaint_model.pt
│   │   └── label_map.json
│   │
│   └── utils
│       └── language_utils.py
│
├── main.py
└── requirements.txt
```

---

## Running the API

Start the FastAPI server:

```
uvicorn main:app --reload
```

Open the interactive documentation:

```
http://127.0.0.1:8000/docs
```

---

## API Endpoint

### POST /predict

Classifies a citizen complaint.

**Request**

```json
{
  "complaint": "pothole near hospital causing accidents"
}
```

**Response**

```json
{
  "category": "infrastructure",
  "issue_type": "potholes",
  "confidence": 0.92
}
```

---

## Error Handling

If the complaint is not a valid civic issue:

```json
{
  "category": "not_recognized",
  "issue_type": "not_recognized",
  "confidence": 1.0
}
```

---

## Use Cases

* Smart City grievance portals
* Municipal complaint management systems
* Government service chatbots
* Automated complaint routing
* Civic data analytics

---

## Advantages

* Reduces manual complaint sorting
* Enables real-time grievance classification
* Supports multilingual citizen interaction
* Prevents category hallucination through constrained taxonomy
* Easily scalable using API-based deployment

---


