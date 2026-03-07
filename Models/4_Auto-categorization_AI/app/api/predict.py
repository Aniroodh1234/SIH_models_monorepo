from fastapi import APIRouter
from pydantic import BaseModel

from app.services.llm_services import hybrid_predict


router = APIRouter()


class ComplaintRequest(BaseModel):
    complaint: str


@router.post("/predict")
def predict_category(request: ComplaintRequest):

    result = hybrid_predict(request.complaint)

    return {
        "status": "success",
        "data": result
    }