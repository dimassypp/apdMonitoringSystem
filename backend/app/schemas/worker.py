from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WorkerCreate(BaseModel):
    """Schema untuk menambah pekerja baru"""
    name: str
    employee_id: Optional[str] = None
    department: Optional[str] = None


class WorkerResponse(BaseModel):
    """Schema untuk response data pekerja"""
    id: int
    name: str
    employee_id: Optional[str]
    department: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True  # Agar bisa baca dari SQLAlchemy model
