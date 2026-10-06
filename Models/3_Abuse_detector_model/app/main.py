from fastapi import FastAPI
from app.api.moderation_route import router as moderation_router

app = FastAPI(
    title="SwarajDesk_Abusive_AI_Detector",
    version="0.1.0",
    description=(
        "API service to detect and mask abusive / disrespectful language "
        "from complaint descriptions (English, Hindi, Hinglish, Odia)."
    ),
)

# Register the moderation routes
app.include_router(moderation_router)


@app.get("/health")
def health_check():
    """
    Simple health endpoint to check if the service is up.
    """
    return {"status": "ok"}
