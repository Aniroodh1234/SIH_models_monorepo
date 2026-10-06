from fastapi import APIRouter
from app.models.schemas import ModerationRequest, ModerationResult
from app.services.pipeline import run_moderation

router = APIRouter(
    prefix="/api/v1",
    tags=["moderation"],
)


@router.post("/moderate", response_model=ModerationResult)
def moderate_text(payload: ModerationRequest):
    """
    Main endpoint:
      - Input: raw user complaint text
      - Output: clean text + abusive spans (if any)
    """
    return run_moderation(payload)
