from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.detection import DetectionStatus


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

class DetectionVerify(BaseModel):
    """Schema untuk verifikasi pengawas"""
    status: DetectionStatus                     # confirmed atau false_alarm
    worker_id: Optional[int] = None
    worker_name_manual: Optional[str] = None    # nama pelanggar
    notes: Optional[str] = None
    verified_by: str                            # nama pengawas