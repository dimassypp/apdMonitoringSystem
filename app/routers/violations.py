"""
Router untuk manajemen pelanggaran APD.
Violations dibuat otomatis saat pengawas konfirmasi detection via /api/detections/{id}/verify.
Router ini hanya untuk READ, statistik dashboard, dan update status.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.violation import Violation, ViolationStatus
from app.schemas.violation import ViolationResponse, ViolationSummary, ViolationStatusUpdate, ViolationVerify

router = APIRouter(prefix="/api/violations", tags=["Violations"])


@router.get("/", response_model=List[ViolationResponse], summary="Ambil semua pelanggaran")
def get_violations(
    status: Optional[ViolationStatus] = None,
    db: Session = Depends(get_db)
):
    """
    Ambil daftar semua pelanggaran.
    Bisa difilter berdasarkan status: unverified, verified, false_alarm.
    """
    query = db.query(Violation)
    if status:
        query = query.filter(Violation.status == status)
    return query.order_by(Violation.created_at.desc()).all()


@router.get("/summary", response_model=ViolationSummary, summary="Statistik ringkasan pelanggaran")
def get_violation_summary(db: Session = Depends(get_db)):
    """Statistik pelanggaran untuk ditampilkan di dashboard."""
    total        = db.query(func.count(Violation.id)).scalar()
    verified     = db.query(func.count(Violation.id)).filter(Violation.status == ViolationStatus.VERIFIED).scalar()
    unverified   = db.query(func.count(Violation.id)).filter(Violation.status == ViolationStatus.UNVERIFIED).scalar()
    false_alarms = db.query(func.count(Violation.id)).filter(Violation.status == ViolationStatus.FALSE_ALARM).scalar()

    missing_helmet = db.query(func.count(Violation.id)).filter(Violation.missing_helmet == True).scalar()
    missing_vest   = db.query(func.count(Violation.id)).filter(Violation.missing_vest   == True).scalar()
    missing_mask   = db.query(func.count(Violation.id)).filter(Violation.missing_mask   == True).scalar()

    return ViolationSummary(
        total_violations=total,
        verified=verified,
        unverified=unverified,
        false_alarms=false_alarms,
        missing_helmet_count=missing_helmet,
        missing_vest_count=missing_vest,
        missing_mask_count=missing_mask
    )


@router.get("/{violation_id}", response_model=ViolationResponse, summary="Ambil detail pelanggaran")
def get_violation(violation_id: int, db: Session = Depends(get_db)):
    violation = db.query(Violation).filter(Violation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Pelanggaran tidak ditemukan")
    return violation


@router.patch("/{violation_id}/status", response_model=ViolationResponse, summary="Update status pelanggaran")
def update_violation_status(
    violation_id: int,
    update_data: ViolationStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update status pelanggaran: verified atau false_alarm."""
    violation = db.query(Violation).filter(Violation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Pelanggaran tidak ditemukan")

    violation.status = update_data.status
    if update_data.verified_by:
        violation.verified_by = update_data.verified_by
    violation.verified_at = datetime.now()

    db.commit()
    db.refresh(violation)
    return violation


@router.patch("/{violation_id}/verify", response_model=ViolationResponse, summary="Verifikasi pelanggaran oleh pengawas")
def verify_violation(
    violation_id: int,
    update_data: ViolationVerify,
    db: Session = Depends(get_db)
):
    """Pengawas update nama pelanggar dan status pelanggaran."""
    violation = db.query(Violation).filter(Violation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Pelanggaran tidak ditemukan")

    if update_data.worker_id:
        violation.worker_id = update_data.worker_id
    if update_data.worker_name_manual:
        violation.worker_name_manual = update_data.worker_name_manual
    if update_data.notes:
        violation.notes = update_data.notes

    violation.status = update_data.status
    violation.verified_by = update_data.verified_by
    violation.verified_at = datetime.now()

    db.commit()
    db.refresh(violation)
    return violation