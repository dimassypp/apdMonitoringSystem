from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DetectionCreate(BaseModel):
    """
    Schema untuk menerima hasil deteksi dari modul AI.
    Ini yang dikirim oleh tim AI (Qudwa) ke endpoint POST /api/detections/
    """
    capture_id: int
    has_helmet: Optional[bool] = None
    has_vest: Optional[bool] = None
    has_mask: Optional[bool] = None
    confidence_score: Optional[float] = None


class DetectionResponse(BaseModel):
    """Schema untuk response hasil deteksi"""
    id: int
    capture_id: int
    has_helmet: Optional[bool]
    has_vest: Optional[bool]
    has_mask: Optional[bool]
    confidence_score: Optional[float]
    detected_at: datetime

    class Config:
        from_attributes = True
