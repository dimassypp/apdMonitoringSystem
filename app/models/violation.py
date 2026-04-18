from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class ViolationStatus(str, enum.Enum):
    """Status verifikasi pelanggaran oleh pengawas K3"""
    UNVERIFIED = "unverified"      # Belum diverifikasi pengawas
    VERIFIED = "verified"           # Dikonfirmasi memang pelanggaran
    FALSE_ALARM = "false_alarm"     # Ternyata bukan pelanggaran (false positive AI)


class Violation(Base):
    """
    Tabel pelanggaran APD.
    
    Alur pengisian:
    1. AI mendeteksi ada yang tidak pakai APD → masuk tabel Detection
    2. Pengawas K3 melihat foto + hasil deteksi
    3. Pengawas input manual: siapa orangnya (worker_name_manual atau pilih worker_id)
    4. Pengawas konfirmasi APD apa yang tidak dipakai
    5. Status bisa diubah jadi verified atau false_alarm
    """
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, ForeignKey("captures.id"), nullable=False)
    detection_id = Column(Integer, ForeignKey("detections.id"), nullable=True)

    # Identitas pelanggar — bisa pilih dari tabel worker, atau input nama manual
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    worker_name_manual = Column(String(100), nullable=True)  # Jika tidak ada di database

    # APD yang tidak dipakai — diisi pengawas, mengkonfirmasi hasil AI
    missing_helmet = Column(Boolean, default=False)
    missing_vest = Column(Boolean, default=False)
    missing_mask = Column(Boolean, default=False)

    notes = Column(Text, nullable=True)           # Catatan tambahan pengawas
    verified_by = Column(String(100), nullable=True)  # Nama pengawas yang input
    verified_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(ViolationStatus), default=ViolationStatus.UNVERIFIED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi
    capture = relationship("Capture", back_populates="violations")
    detection = relationship("Detection", back_populates="violations")
    worker = relationship("Worker", back_populates="violations")
