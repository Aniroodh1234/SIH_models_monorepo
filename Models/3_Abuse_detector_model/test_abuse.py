import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.pipeline import run_moderation
from app.models.schemas import ModerationRequest

def test():
    text = "You are a very bad person and I hate you so much, fuck you!"
    req = ModerationRequest(text=text)
    print("Running moderation pipeline...")
    res = run_moderation(req)
    print("Result:")
    print("has_abuse:", res.has_abuse)
    print("clean_text:", res.clean_text)
    print("severity:", res.severity)
    print("flagged_spans:", res.flagged_spans)

if __name__ == "__main__":
    test()
