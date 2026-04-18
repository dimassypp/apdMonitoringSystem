from sqlalchemy import Column, Integer, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Detection(Base):
    """
    Tabel hasil analisis AI terhadap foto.
    Data ini dikirim oleh modul AI (branch ai-model) ke endpoint backend.
    
    has_helmet, has_vest, has_mask = True jika APD terdeteksi dipakai,
    False jika tidak terdeteksi / tidak dipakai.
    """
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, ForeignKey("captures.id"), unique=True, nullable=False)

    # Hasil deteksi APD dari model AI
    has_helmet = Column(Boolean, nullable=True)   # True = pakai helm, False = tidak
    has_vest = Column(Boolean, nullable=True)     # True = pakai rompi, False = tidak
    has_mask = Column(Boolean, nullable=True)     # True = pakai masker, False = tidak

    # Tingkat keyakinan model AI (0.0 - 1.0), opsional
    confidence_score = Column(Float, nullable=True)

    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi ke capture
    capture = relationship("Capture", back_populates="detection")
    violations = relationship("Violation", back_populates="detection")
