"""
Router untuk manajemen pelanggaran APD.
Ini adalah bagian utama yang dipakai pengawas K3 untuk mencatat pelanggaran.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.violation import Violation, ViolationStatus
from app.models.capture import Capture
from app.schemas.violation import (
    ViolationCreate, ViolationStatusUpdate,
    ViolationResponse, ViolationSummary
)
from app.utils.notification import send_telegram

router = APIRouter(prefix="/api/violations", tags=["Violations"])


@router.post("/", response_model=ViolationResponse, summary="Catat pelanggaran APD")
def create_violation(violation_data: ViolationCreate, db: Session = Depends(get_db)):
    """
    Catat pelanggaran APD — diisi oleh pengawas K3 setelah melihat foto dan hasil AI.
    
    Pengawas mengisi:
    - capture_id: foto mana yang ada pelanggarannya
    - worker_id atau worker_name_manual: siapa pelanggarnya (input manual pengawas)
    - missing_helmet/vest/mask: APD apa yang tidak dipakai
    - verified_by: nama pengawas yang mencatat
    
    Contoh body request:
    {
        "capture_id": 1,
        "worker_name_manual": "Budi Santoso",
        "missing_helmet": true,
        "missing_vest": false,
        "missing_mask": false,
        "notes": "Terlihat di area loading dock",
        "verified_by": "Pak Agus (Pengawas K3)"
    }
    """
    # Validasi capture ada
    capture = db.query(Capture).filter(Capture.id == violation_data.capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture tidak ditemukan")

    # Minimal harus ada nama pekerja (dari database atau manual)
    if not violation_data.worker_id and not violation_data.worker_name_manual:
        raise HTTPException(
            status_code=400,
            detail="Harus isi worker_id atau worker_name_manual untuk identifikasi pelanggar"
        )

    # Minimal harus ada satu APD yang dilanggar
    if not (violation_data.missing_helmet or violation_data.missing_vest or violation_data.missing_mask):
        raise HTTPException(
            status_code=400,
            detail="Minimal satu APD harus ditandai tidak dipakai"
        )

    violation = Violation(
        **violation_data.model_dump(),
        status=ViolationStatus.UNVERIFIED,
        verified_at=datetime.now() if violation_data.verified_by else None
    )
    db.add(violation)
    db.commit()
    db.refresh(violation)

        # Kirim notifikasi Telegram
    apd_list = []
    if violation_data.missing_helmet:
        apd_list.append("Helm")
    if violation_data.missing_vest:
        apd_list.append("Rompi")
    if violation_data.missing_mask:
        apd_list.append("Masker")

    nama = violation_data.worker_name_manual or f"Worker ID {violation_data.worker_id}"
    apd_str = ", ".join(apd_list)

    send_telegram(
        f"<b>Pelanggaran APD Terdeteksi</b>\n\n"
        f"Pelanggar: {nama}\n"
        f"APD tidak dipakai: {apd_str}\n"
        f"Lokasi: {violation_data.notes or '-'}\n"
        f"Dicatat oleh: {violation_data.verified_by or '-'}"
    )

    return violation


@router.get("/", response_model=List[ViolationResponse], summary="Ambil semua pelanggaran")
def get_violations(
    status: Optional[ViolationStatus] = None,
    db: Session = Depends(get_db)
):
    """
    Ambil daftar semua pelanggaran.
    Bisa difilter berdasarkan status: unverified, verified, false_alarm.
    Dipakai untuk dashboard monitoring.
    """
    query = db.query(Violation)
    if status:
        query = query.filter(Violation.status == status)
    return query.order_by(Violation.created_at.desc()).all()


@router.get("/summary", response_model=ViolationSummary, summary="Statistik ringkasan pelanggaran")
def get_violation_summary(db: Session = Depends(get_db)):
    """
    Ambil statistik ringkasan pelanggaran untuk ditampilkan di dashboard.
    Menampilkan: total, per-status, dan jenis APD yang paling sering dilanggar.
    """
    total = db.query(func.count(Violation.id)).scalar()
    verified = db.query(func.count(Violation.id)).filter(Violation.status == ViolationStatus.VERIFIED).scalar()
    unverified = db.query(func.count(Violation.id)).filter(Violation.status == ViolationStatus.UNVERIFIED).scalar()
    false_alarms = db.query(func.count(Violation.id)).filter(Violation.status == ViolationStatus.FALSE_ALARM).scalar()

    missing_helmet = db.query(func.count(Violation.id)).filter(Violation.missing_helmet == True).scalar()
    missing_vest = db.query(func.count(Violation.id)).filter(Violation.missing_vest == True).scalar()
    missing_mask = db.query(func.count(Violation.id)).filter(Violation.missing_mask == True).scalar()

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
    """
    Update status pelanggaran oleh pengawas K3.
    
    Status yang bisa dipilih:
    - verified: dikonfirmasi memang pelanggaran nyata
    - false_alarm: ternyata bukan pelanggaran (AI salah deteksi)
    
    Contoh body:
    {
        "status": "verified",
        "verified_by": "Pak Agus"
    }
    """
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
