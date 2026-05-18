from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class CaptureStatus(str, enum.Enum):
    """Status foto yang diupload"""
    PENDING = "pending"          # Baru diupload, belum diproses AI
    ENHANCED = "enhanced"        # Sudah di-enhance, siap dikirim ke AI
    PROCESSED = "processed"      # Sudah dianalisis AI


class Capture(Base):
    """
    Tabel foto yang di-capture dari kamera CCTV.
    Alur: upload foto → enhance → kirim ke AI → hasil deteksi masuk ke tabel Detection
    """
    __tablename__ = "captures"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String(500), nullable=False)           # Path foto asli
    image_enhanced_path = Column(String(500), nullable=True)   # Path foto setelah di-enhance
    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(CaptureStatus), default=CaptureStatus.PENDING)

    # Relasi ke tabel deteksi dan pelanggaran
    detection = relationship("Detection", back_populates="capture", uselist=False)
    violations = relationship("Violation", back_populates="capture")
