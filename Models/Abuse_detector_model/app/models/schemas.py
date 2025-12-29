from typing import List, Optional
from pydantic import BaseModel


class ModerationRequest(BaseModel):
    """
    Incoming request from SwarajDesk backend.
    """
    text: str
    complaint_id: Optional[str] = None
    user_id: Optional[str] = None


class FlaggedSpan(BaseModel):
    """
    One abusive / disrespectful word or phrase detected in the text.
    Positions are character indices in the original string.
    """
    start: int                    # inclusive index in original_text
    end: int                      # exclusive index in original_text
    original: str                   # original abusive word/phrase
    masked: Optional[str] = None     # what we replaced it with (e.g., "******")
    lang: Optional[str] = None       # "en", "hi", "hinglish", "odia", or None
    category: Optional[str] = None    # e.g., "abuse", "slur", "sexual", etc.
    severity: Optional[str] = None    # "low", "medium", "high"
    confidence: Optional[float] = None    # 0.0–1.0 (from model, later)


class ModerationResult(BaseModel):
    """
    Final response from our service.
    """
    has_abuse: bool                 # True if at least one abusive span found
    original_text: str              # exact user input
    clean_text: str                 # text with abusive parts replaced by "******"
    severity: str                   # overall severity: "none"/"low"/"medium"/"high"
    flagged_spans: List[FlaggedSpan]
