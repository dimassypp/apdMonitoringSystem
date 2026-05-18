from sqlalchemy import Column, Integer, Boolean, Float, DateTime, ForeignKey, String, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class DetectionStatus(str, enum.Enum):
    UNVERIFIED = "unverified"    # Menunggu verifikasi pengawas
    CONFIRMED  = "confirmed"     # Dikonfirmasi pelanggaran → pengawas buat violation
    FALSE_ALARM = "false_alarm"  # Ternyata bukan pelanggaran


class Detection(Base):
    __tablename__ = "detections"

    id               = Column(Integer, primary_key=True, index=True)
    capture_id       = Column(Integer, ForeignKey("captures.id"), unique=True, nullable=False)
    has_helmet       = Column(Boolean, nullable=True)
    has_vest         = Column(Boolean, nullable=True)
    has_mask         = Column(Boolean, nullable=True)
    confidence_score = Column(Float, nullable=True)
    camera_location  = Column(String(200), nullable=True)
    status           = Column(Enum(DetectionStatus), default=DetectionStatus.UNVERIFIED)
    detected_at      = Column(DateTime(timezone=True), server_default=func.now())

    capture    = relationship("Capture", back_populates="detection")
    violations = relationship("Violation", back_populates="detection")