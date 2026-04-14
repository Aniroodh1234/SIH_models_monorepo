
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ReportResponse(BaseModel):
    """Response containing all 3 generated reports."""

    success: bool = True
    category: str
    resolved_category: str = Field(
        description="The resolved category after fuzzy matching."
    )
    survey_report: Dict[str, Any] = Field(
        description="JSON Report 1 — Survey/NGO generalized report"
    )
    backend_report: Dict[str, Any] = Field(
        description="JSON Report 2 — SwarajDesk backend complaint report"
    )
    fusion_report: Dict[str, Any] = Field(
        description="JSON Report 3 — Fusion of both reports"
    )
    pipeline_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pipeline execution metadata (timing, etc.)"
    )


class ErrorResponse(BaseModel):
    """Standardized error response."""

    success: bool = False
    error: str
    detail: Optional[str] = None
    valid_categories: Optional[List[str]] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    model: str
    vector_stores: Dict[str, Any]
