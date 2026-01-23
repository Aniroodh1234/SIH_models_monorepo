from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from mangum import Mangum

from app import answer_user_query, collection
from voice_routes import router as voice_router   


app = FastAPI(title="Swaraj_chat Backend API")


# ----- CORS -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # later restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve audio response files (voice output)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ----- request model -----
class ChatRequest(BaseModel):
    user_query: str
    language: str = "english"


# ----- response model -----
class ChatResponse(BaseModel):
    bot_response: str


# ----- /chat endpoint (text input) -----
@app.post("/chat_swaraj", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    # Validate Content-Type
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        raise HTTPException(status_code=415, detail="Content-Type must be application/json")

    # Same RAG pipeline as before
    answer = answer_user_query(req.user_query, collection, req.language)
    return ChatResponse(bot_response=answer)


# ----- include voice bot API (WAV/MP3 input + MP3 output) -----
app.include_router(voice_router)


# ----- basic verification endpoint -----
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"status": "This is the SwarajDesk RAG-Based Multilingual Chatbot Backend"}

handler = Mangum(app)

