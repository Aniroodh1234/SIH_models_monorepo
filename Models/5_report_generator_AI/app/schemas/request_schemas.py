
from pydantic import BaseModel, Field
from typing import Optional


class SurveyReportRequest(BaseModel):
    """Request body for POST /survey-report"""

    category: str = Field(
        ...,
        description="Category for the report (e.g., 'Infrastructure', 'Health'). "
                    "Supports exact names and free-text fuzzy matching.",
        examples=["Infrastructure", "Water Supply & Sanitation", "water pollution"],
    )
