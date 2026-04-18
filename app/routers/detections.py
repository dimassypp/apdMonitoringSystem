"""
Router untuk hasil deteksi AI.
Endpoint ini dipanggil oleh modul AI (branch ai-model) setelah selesai menganalisis foto.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.capture import Capture, CaptureStatus
from app.models.detection import Detection
from app.schemas.detection import DetectionCreate, DetectionResponse

router = APIRouter(prefix="/api/detections", tags=["Detections"])


@router.post("/", response_model=DetectionResponse, summary="Kirim hasil deteksi AI")
def create_detection(detection_data: DetectionCreate, db: Session = Depends(get_db)):
    """
    Endpoint ini dipanggil oleh modul AI setelah menganalisis foto.
    
    Modul AI (Qudwa) akan:
    1. Ambil foto dari GET /api/captures/{id}/enhanced
    2. Analisis foto dengan model YOLO
    3. Kirim hasilnya ke endpoint ini
    
    Body yang dikirim AI:
    {
        "capture_id": 1,
        "has_helmet": false,
        "has_vest": true,
        "has_mask": false,
        "confidence_score": 0.87
    }
    """
    # Pastikan capture_id valid
    capture = db.query(Capture).filter(Capture.id == detection_data.capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture tidak ditemukan")

    # Cek apakah deteksi untuk capture ini sudah ada
    existing = db.query(Detection).filter(Detection.capture_id == detection_data.capture_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Deteksi untuk capture ini sudah ada")

    # Simpan hasil deteksi
    detection = Detection(**detection_data.model_dump())
    db.add(detection)

    # Update status capture menjadi 'processed'
    capture.status = CaptureStatus.PROCESSED
    db.commit()
    db.refresh(detection)

    return detection


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
