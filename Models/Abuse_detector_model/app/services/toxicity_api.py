import httpx
from app.config import settings


MODEL_URL = "https://router.huggingface.co/hf-inference/models/unitary/unbiased-toxic-roberta"



async def get_toxicity_score(text: str) -> float:
    headers = {"Authorization": f"Bearer {settings.HF_API_KEY}"}
    payload = {"inputs": text}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(MODEL_URL, json=payload, headers=headers)

    result = response.json()

    # HANDLE API ERRORS INSTEAD OF CRASHING
    if isinstance(result, dict) and "error" in result:
        # Model might be loading (first call),
        # so return neutral toxicity score.
        print("HF returned error:", result["error"])
        return 0.0

    if isinstance(result, dict) and "estimated_time" in result:
        # Model is still loading on Hugging Face servers
        print("Model still loading........")
        return 0.0

    # Normal response: list of list of label-score dicts
    scores = {item["label"]: item["score"] for item in result[0]}

    # highest score will be used as toxicity
    return max(scores.values())

from app.config import settings
