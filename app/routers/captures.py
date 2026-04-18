"""
Router untuk manajemen capture foto dari CCTV.
Alur: upload foto → enhance otomatis → foto siap dikirim ke AI
"""

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.capture import Capture, CaptureStatus
from app.schemas.capture import CaptureResponse
from app.utils.image_enhance import enhance_image

router = APIRouter(prefix="/api/captures", tags=["Captures"])

# Ambil folder upload dari environment variable, default ke "uploads"
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=CaptureResponse, summary="Upload foto dari CCTV")
async def upload_capture(
    file: UploadFile = File(..., description="File foto dari CCTV (jpg/png)"),
    camera_location: Optional[str] = Form(None, description="Lokasi kamera, contoh: Area Receiving"),
    db: Session = Depends(get_db)
):
    """
    Upload foto yang di-capture dari CCTV.
    Setelah upload, foto otomatis di-enhance untuk memperjelas detail APD.
    
    Response berisi path foto asli dan foto yang sudah di-enhance.
    """
    # Validasi tipe file
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        raise HTTPException(status_code=400, detail="Hanya file JPG dan PNG yang diterima")

    # Buat nama file unik agar tidak bertabrakan
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    save_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Simpan file asli ke disk
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Enhance foto otomatis setelah upload
    try:
        enhanced_path = enhance_image(save_path, UPLOAD_DIR)
        status = CaptureStatus.ENHANCED
    except Exception as e:
        # Jika enhance gagal, tetap simpan foto asli
        enhanced_path = None
        status = CaptureStatus.PENDING

    # Simpan data ke database
    capture = Capture(
        image_path=save_path,
        image_enhanced_path=enhanced_path,
        camera_location=camera_location,
        status=status
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)

    return capture


@router.get("/", response_model=list[CaptureResponse], summary="Ambil semua data capture")
def get_captures(
    status: Optional[CaptureStatus] = None,
    db: Session = Depends(get_db)
):
    """
    Ambil daftar semua foto yang pernah di-capture.
    Bisa difilter berdasarkan status: pending, enhanced, atau processed.
    """
    query = db.query(Capture)
    if status:
        query = query.filter(Capture.status == status)
    return query.order_by(Capture.captured_at.desc()).all()


@router.get("/{capture_id}", response_model=CaptureResponse, summary="Ambil data capture by ID")
def get_capture(capture_id: int, db: Session = Depends(get_db)):
    capture = db.query(Capture).filter(Capture.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture tidak ditemukan")
    return capture


@router.get("/{capture_id}/image", summary="Lihat foto asli")
def get_capture_image(capture_id: int, db: Session = Depends(get_db)):
    """Endpoint untuk menampilkan file foto asli."""
    capture = db.query(Capture).filter(Capture.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture tidak ditemukan")
    if not os.path.exists(capture.image_path):
        raise HTTPException(status_code=404, detail="File foto tidak ditemukan")
    return FileResponse(capture.image_path)


@router.get("/{capture_id}/enhanced", summary="Lihat foto yang sudah di-enhance")
def get_enhanced_image(capture_id: int, db: Session = Depends(get_db)):
    """Endpoint untuk menampilkan foto yang sudah di-enhance (lebih jelas untuk AI)."""
    capture = db.query(Capture).filter(Capture.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture tidak ditemukan")
    if not capture.image_enhanced_path or not os.path.exists(capture.image_enhanced_path):
        raise HTTPException(status_code=404, detail="Foto enhanced belum tersedia")
    return FileResponse(capture.image_enhanced_path)
