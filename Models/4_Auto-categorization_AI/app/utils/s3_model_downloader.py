import os
import boto3

MODEL_BUCKET = "ai-categorize-model-bucket"

MODEL_KEY = "models/distilbert_complaint_model.pt"
LABEL_KEY = "models/label_map.json"

MODEL_PATH = "app/models/distilbert_complaint_model.pt"
LABEL_PATH = "app/models/label_map.json"


def download_model():

    os.makedirs("app/models", exist_ok=True)

    s3 = boto3.client("s3")

    if not os.path.exists(MODEL_PATH):
        print("Downloading model from S3...")
        s3.download_file(MODEL_BUCKET, MODEL_KEY, MODEL_PATH)

    if not os.path.exists(LABEL_PATH):
        print("Downloading label map from S3...")
        s3.download_file(MODEL_BUCKET, LABEL_KEY, LABEL_PATH)