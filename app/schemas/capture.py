from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.capture import CaptureStatus


class CaptureResponse(BaseModel):
    """Schema untuk response data capture"""
    id: int
    image_path: str
    image_enhanced_path: Optional[str]
    captured_at: datetime
    status: CaptureStatus

    class Config:
        from_attributes = True
