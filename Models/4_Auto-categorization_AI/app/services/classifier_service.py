import os
import json
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# Get project root safely
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "models")

MODEL_PATH = os.path.join(MODELS_DIR, "distilbert_complaint_model.pt")
LABEL_MAP_PATH = os.path.join(MODELS_DIR, "label_map.json")

MODEL_NAME = "distilbert-base-uncased"


# Verify files exist
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

if not os.path.exists(LABEL_MAP_PATH):
    raise FileNotFoundError(f"Label map file not found: {LABEL_MAP_PATH}")


# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


# Load label map
with open(LABEL_MAP_PATH, "r", encoding="utf-8") as f:
    label_map = json.load(f)

id_to_label = {v: k for k, v in label_map.items()}


# Load model architecture
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(label_map)
)

# Load trained weights
model.load_state_dict(
    torch.load(MODEL_PATH, map_location=torch.device("cpu"))
)

model.eval()


def predict_category(text: str):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)

    logits = outputs.logits
    probs = F.softmax(logits, dim=1)

    confidence, predicted_class_id = torch.max(probs, dim=1)

    predicted_label = id_to_label[predicted_class_id.item()]

    return {
        "category": predicted_label,
        "confidence": float(confidence.item())
    }