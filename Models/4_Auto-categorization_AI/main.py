from fastapi import FastAPI

from app.api.predict import router as predict_router


app = FastAPI(
    title="SwarajDesk AI Complaint Classifier",
    description="Hybrid AI system for multilingual civic complaint categorization",
    version="1.0"
)

@app.get("/")
def root():
    return {"message": "SwarajDesk AI categorization"}

app.include_router(predict_router)