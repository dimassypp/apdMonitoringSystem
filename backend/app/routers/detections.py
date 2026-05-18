from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import os

from app.database import get_db
from app.models.capture import Capture, CaptureStatus
from app.models.detection import Detection, DetectionStatus
from app.schemas.detection import DetectionCreate, DetectionResponse, DetectionVerify

router = APIRouter(prefix="/api/detections", tags=["Detections"])


@router.post("/report", summary="AI laporkan anomali — foto + hasil deteksi sekaligus")
async def report_anomaly(
    file: UploadFile = File(...),
    camera_location: Optional[str] = Form(None),
    has_helmet: bool = Form(...),
    has_vest: bool = Form(...),
    has_mask: bool = Form(...),
    confidence_score: Optional[float] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Dipanggil AI saat mendeteksi anomali.
    1. Simpan frame sebagai capture
    2. Simpan hasil deteksi (status: unverified)
    3. Kirim notifikasi Telegram ke pengawas
    Pengawas yang kemudian verifikasi dan buat violation.
    """
    import uuid
    from app.models.capture import Capture, CaptureStatus
    from app.utils.image_enhance import enhance_image
    from app.utils.notification import send_telegram

    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

    # 1. Simpan foto frame
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    save_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 2. Enhance foto
    try:
        enhanced_path = enhance_image(save_path, UPLOAD_DIR)
    except Exception:
        enhanced_path = None

    # 3. Simpan capture
    capture = Capture(
        image_path=save_path,
        image_enhanced_path=enhanced_path,
        status=CaptureStatus.PROCESSED
    )
    db.add(capture)
    db.flush()

    # 4. Simpan hasil deteksi — status unverified, menunggu pengawas
    detection = Detection(
        capture_id=capture.id,
        has_helmet=has_helmet,
        has_vest=has_vest,
        has_mask=has_mask,
        confidence_score=confidence_score,
        camera_location=camera_location,
        status=DetectionStatus.UNVERIFIED
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)

    # 5. Kirim Telegram — beritahu pengawas ada yang perlu diverifikasi
    apd_list = []
    if not has_helmet: apd_list.append("Helm")
    if not has_vest:   apd_list.append("Rompi")
    if not has_mask:   apd_list.append("Masker")

    send_telegram(
        f"<b>Anomali APD Terdeteksi</b>\n\n"
        f"APD tidak terdeteksi: {', '.join(apd_list)}\n"
        f"Lokasi: {camera_location or '—'}\n"
        f"Confidence: {confidence_score or '—'}\n"
        f"Detection ID: {detection.id}\n\n"
        f"Silakan verifikasi di dashboard."
    )

    return {
        "capture_id":   capture.id,
        "detection_id": detection.id,
        "status":       "unverified",
        "message":      "Anomali tercatat, menunggu verifikasi pengawas"
    }


@router.get("/{capture_id}", response_model=DetectionResponse, summary="Ambil hasil deteksi by capture ID")
def get_detection_by_capture(capture_id: int, db: Session = Depends(get_db)):
    """
    Ambil hasil deteksi AI berdasarkan capture_id.
    Dipakai pengawas K3 untuk lihat hasil AI sebelum input manual pelanggarnya.
    """
    detection = db.query(Detection).filter(Detection.capture_id == capture_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Hasil deteksi belum ada untuk capture ini")
    return detection

@router.patch("/{detection_id}/verify", summary="Pengawas verifikasi hasil deteksi AI")
def verify_detection(
    detection_id: int,
    verify_data: DetectionVerify,
    db: Session = Depends(get_db)
):
    """
    Pengawas verifikasi setelah lihat foto dan hasil deteksi di dashboard.
    
    Kalau confirmed → otomatis buat violation baru dengan nama pelanggar
    Kalau false_alarm → detection ditandai false alarm, selesai
    """
    from app.models.violation import Violation, ViolationStatus

    detection = db.query(Detection).filter(Detection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection tidak ditemukan")

    # Update status detection
    detection.status = verify_data.status
    db.flush()

    violation = None

    # Kalau dikonfirmasi pelanggaran → buat violation
    if verify_data.status == DetectionStatus.CONFIRMED:
        violation = Violation(
            capture_id=detection.capture_id,
            detection_id=detection.id,          # ← tambah ini
            worker_id=verify_data.worker_id,
            worker_name_manual=verify_data.worker_name_manual,
            missing_helmet=not detection.has_helmet,
            missing_vest=not detection.has_vest,
            missing_mask=not detection.has_mask,
            notes=verify_data.notes,
            verified_by=verify_data.verified_by,
            verified_at=datetime.now(),
            status=ViolationStatus.VERIFIED
        )
        db.add(violation)

    db.commit()

    return {
        "detection_id": detection.id,
        "status":       detection.status,
        "violation_id": violation.id if violation else None,
        "message":      "Pelanggaran dicatat" if violation else "Ditandai false alarm"
    }