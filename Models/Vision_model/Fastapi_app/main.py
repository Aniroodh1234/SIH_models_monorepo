import os
from dotenv import load_dotenv
load_dotenv()

## Groq api key and setting hugging face environment
Groq_api_key = os.getenv('GROQ_API_KEY')
os.environ['HUGGINGFACEHUB_API_TOKEN']=os.getenv("HUGGINGFACEHUB_API_TOKEN")

## Langsmith tracking
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"]="true"
os.environ["LANGCHAIN_PROJECT"]="You_current_project_name"


from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from .inference import predict_issue_hybrid
from .utils import download_image_from_url

app = FastAPI(title="SwarajDesk_CV_API (Hybrid VLM + ViT)", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ImageUrlRequest(BaseModel):
    image_url: str

@app.get("/")
def home():
    return {"status": "API Running", "mode": "hybrid_vlm_vit_20_sectors"}

@app.post("/predict")
async def predict(
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None)
):
    """
    Predict issue from image.
    Accepts either:
    - image: File upload (multipart/form-data)
    - image_url: CDN image URL (as form field in multipart/form-data)
    
    Usage examples:
    1. File upload: POST /predict with form-data, key="image", value=<file>
    2. URL: POST /predict with form-data, key="image_url", value="https://cdn.example.com/image.jpg"
    """
    image_bytes = None
    
    # Check if file is provided
    if image is not None:
        image_bytes = await image.read()
    # Check if URL is provided
    elif image_url:
        try:
            image_bytes = download_image_from_url(image_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(
            status_code=400, 
            detail="Either 'image' (file upload) or 'image_url' (CDN URL) must be provided"
        )
    
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Failed to load image data")
    
    result = predict_issue_hybrid(image_bytes)
    return result

@app.post("/predict-from-url")
async def predict_from_url(request: ImageUrlRequest):
    """
    Alternative endpoint for URL-based predictions (JSON body).
    Accepts JSON: {"image_url": "https://..."}
    """
    try:
        image_bytes = download_image_from_url(request.image_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    result = predict_issue_hybrid(image_bytes)
    return result

