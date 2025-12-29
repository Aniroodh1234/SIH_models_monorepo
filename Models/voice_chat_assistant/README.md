# Intelligent Citizen Support Platform — AI-Powered Multilingual RAG and Voice Assistance

A multilingual, retrieval-augmented support system designed to assist citizens with SwarajDesk services through natural language interaction. The platform provides accurate, policy-grounded responses using a RAG pipeline, supports voice-based queries and responses, and seamlessly redirects users to human support when required.

## 1. Overview

This project implements an AI-driven public helpdesk capable of understanding and responding to user queries in English, Hindi, and Hinglish through both text and voice interactions. It integrates:

- Retrieval-Augmented Generation (RAG) for strictly context-based responses
- Multilingual LLM reasoning using Groq's inference models
- Speech-to-Text (STT) and Text-to-Speech (TTS) for real-time audio assistance
- A fully containerizable and deployable FastAPI backend
- ChromaDB for vector search over verified SwarajDesk policies and documents

The system ensures reliability, transparency, and factual accuracy by answering exclusively from the vetted knowledge base and escalating out-of-scope queries to human support.

## 2. Features

### Core Functionalities

- Multilingual support for English, Hindi, Hinglish (text + voice)
- Voice-based interaction with automatic audio format handling (mp3, wav, m4a, webm, ogg)
- Fully context-grounded answers using RAG; zero hallucinations
- Automatic escalation to support or admin for unresolved issues
- FastAPI backend with modular architecture and production-ready routing
- High-performance inference using Groq LLM APIs
- Persistent vector store using ChromaDB

### Voice Pipeline

- Speech-to-Text using audio preprocessing with FFmpeg + Google STT
- Text-to-Speech using gTTS with dynamic language selection
- Robust audio conversion pipeline that normalizes all input formats

### Reliability & Safety

- Strict system prompts ensuring rule-bound responses
- Automatic fallback logic for:
  - Out-of-domain queries
  - Insufficient context
  - Ambiguous intent
- Support escalation paths:
  - General Support: https://swarajdesk.in/support
  - Admin Assistance: https://swarajdesk.in/admin-assist

## 3. Technology Stack

- **Backend Framework:** FastAPI
- **LLM Inference:** Groq (openai/gpt-oss-120b)
- **Vector Database:** ChromaDB (HNSW cosine similarity)
- **Embeddings Model:** paraphrase-multilingual-MiniLM-L12-v2
- **Speech Processing:** FFmpeg, pydub, Python SpeechRecognition
- **Text-to-Speech:** gTTS
- **Environment Management:** Python 3.10+, venv
- **Deployment:** AWS EC2 (Ubuntu 22.04)
- **API Standards:** REST, JSON input/output
- **Security:** CORS management, environment-based secrets

## 4. Project Structure
```
SwarajDesk_chatbot/
│
├── main.py                     # FastAPI entrypoint for text + voice endpoints
├── app.py                      # Core RAG logic and model workflow
├── voice_routes.py             # Voice-chat API (STT → RAG → TTS)
├── speech_to_text.py           # Audio preprocessing + STT
├── text_to_speech.py           # gTTS-based TTS conversion
│
├── SwarajDesk_vectorDB.json    # Document knowledge base
├── chroma_store/               # Persistent ChromaDB vector storage
│
├── static/
│   └── voice/                  # Temporary generated audio files
│
├── requirements.txt
├── .env (ignored)
└── README.md
```

## 5. Installation & Setup

### Step 1: Clone Repository
```bash
git clone <your-repo-url>
cd SwarajDesk_chatbot
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file:
```
GROQ_API_KEY=your_groq_key
HUGGINGFACEHUB_API_TOKEN=your_hf_key
LANGCHAIN_API_KEY=your_langchain_key   # optional
```

### Step 5: Ensure FFmpeg is Installed

For Ubuntu:
```bash
sudo apt update
sudo apt install ffmpeg
```

For Windows, download FFmpeg and add it to PATH.

## 6. Running the Application Locally

### Start the FastAPI server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

#### 1. Text-based Chat

**POST** `/chat_swaraj`

Body:
```json
{
  "user_query": "How can I reset my password?",
  "language": "english"
}
```

#### 2. Voice-based Chat

**POST** `/voice-chat`

Multipart Form Data:

- `file`: audio file
- `language`: english | hindi | hinglish

## 7. RAG Pipeline Overview

1. User query (text or transcribed voice) is converted to English for semantic uniformity.
2. Embeddings generated via multilingual MiniLM.
3. ChromaDB returns top-k relevant context chunks.
4. Groq LLM (gpt-oss-120b) generates responses strictly using given context.
5. Output is translated back to the user's target language for voice synthesis.
6. gTTS produces final audio output in mp3.

## 8. Deployment Guide (AWS EC2)

1. Launch Ubuntu EC2 instance (t3.medium recommended).
2. Install Python, Git, FFmpeg, and pip.
3. Clone repository to EC2.
4. Create a virtual environment and install dependencies.
5. Add secrets to `.env`.
6. Allow inbound rules for port 8000.
7. Start backend server:
```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
```

8. Access from browser:
```
http://<EC2-Public-IP>:8000/docs
```

## 9. Key Strengths of the System

- End-to-end multilingual understanding and generation
- Voice-enabled interaction for accessibility
- Guaranteed correctness through strict RAG enforcement
- Scalable architecture capable of supporting additional regional languages
- High inference speed powered by Groq
- Production-grade modular backend design
- Secure, stateless, cloud-deployable APIs
