from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.violation import ViolationStatus


class ViolationCreate(BaseModel):
    """
    Schema untuk mencatat pelanggaran — diisi pengawas K3 setelah lihat hasil deteksi AI.
    
    Pengawas harus isi:
    - capture_id: foto mana yang dilanggar
    - worker_id ATAU worker_name_manual: siapa pelanggarnya
    - missing_helmet/vest/mask: APD apa yang tidak dipakai
    - verified_by: nama pengawas yang mencatat
    """
    capture_id: int
    detection_id: Optional[int] = None

    # Identitas pelanggar — pilih salah satu atau keduanya
    worker_id: Optional[int] = None
    worker_name_manual: Optional[str] = None

    # Konfirmasi APD yang tidak dipakai
    missing_helmet: bool = False
    missing_vest: bool = False
    missing_mask: bool = False

    notes: Optional[str] = None
    verified_by: Optional[str] = None


class ViolationStatusUpdate(BaseModel):
    """Schema untuk update status pelanggaran (verified / false_alarm)"""
    status: ViolationStatus
    verified_by: Optional[str] = None


class ViolationResponse(BaseModel):
    """Schema untuk response data pelanggaran"""
    id: int
    capture_id: int
    detection_id: Optional[int]
    worker_id: Optional[int]
    worker_name_manual: Optional[str]
    missing_helmet: bool
    missing_vest: bool
    missing_mask: bool
    notes: Optional[str]
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    status: ViolationStatus
    created_at: datetime

    class Config:
        from_attributes = True


class ViolationSummary(BaseModel):
    """Schema untuk ringkasan statistik pelanggaran (dipakai di dashboard)"""
    total_violations: int
    verified: int
    unverified: int
    false_alarms: int
    missing_helmet_count: int
    missing_vest_count: int
    missing_mask_count: int
