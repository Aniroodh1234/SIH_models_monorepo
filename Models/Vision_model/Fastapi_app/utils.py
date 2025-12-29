import torch
from PIL import Image
from torchvision import transforms
import requests
from io import BytesIO

# Image transform for ViT
image_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])

def download_image_from_url(url: str) -> bytes:
    """Download image from CDN URL and return as bytes"""
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Check if content type is an image
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise ValueError(f"URL does not point to an image. Content-Type: {content_type}")
        
        return response.content
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to download image from URL: {str(e)}")

def load_image(image_file):
    """Convert uploaded file to tensor for model"""
    image = Image.open(image_file).convert("RGB")
    return image_transforms(image).unsqueeze(0)  # shape: (1, 3, 224, 224)

def get_top_class(logits):
    """Get class name & confidence from logits"""
    probs = torch.softmax(logits, dim=1)
    confidence, predicted_class = torch.max(probs, dim=1)
    return predicted_class.item(), float(confidence.item())
