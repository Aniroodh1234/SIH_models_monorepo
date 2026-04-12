"""
Pydantic request schemas for the API.
"""

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


class AnalyzeReportRequest(BaseModel):
    """Request body for POST /analyze-report (placeholder)"""

    category: str = Field(
        "All",
        description="Category for the analysis report. Use 'All' to generate a comprehensive report across all categories.",
    )
    date_from: Optional[str] = Field(
        None,
        description="Start date filter (ISO format).",
    )
    date_to: Optional[str] = Field(
        None,
        description="End date filter (ISO format).",
    )
