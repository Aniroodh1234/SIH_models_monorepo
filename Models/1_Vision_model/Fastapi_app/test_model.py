import sys
import os

# Add the Fastapi_app directory to the path so we can import from it
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from inference import predict_issue_hybrid
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

if __name__ == "__main__":
    # Test with pothole.jpg
    image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Test_Images", "pothole.jpg")
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    print("Running prediction...")
    try:
        result = predict_issue_hybrid(image_bytes)
        print("Prediction successful:")
        print(result)
    except Exception as e:
        print(f"Error during prediction: {e}")
