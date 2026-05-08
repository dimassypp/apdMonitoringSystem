from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class ViolationStatus(str, enum.Enum):
    VERIFIED    = "verified"
    UNVERIFIED  = "unverified"
    FALSE_ALARM = "false_alarm"


class Violation(Base):
    __tablename__ = "violations"

    id                  = Column(Integer, primary_key=True, index=True)
    capture_id          = Column(Integer, ForeignKey("captures.id"), nullable=False)
    detection_id        = Column(Integer, ForeignKey("detections.id"), nullable=True)  # ← pastikan ada ForeignKey

    worker_id           = Column(Integer, ForeignKey("workers.id"), nullable=True)
    worker_name_manual  = Column(String(100), nullable=True)

    missing_helmet      = Column(Boolean, default=False)
    missing_vest        = Column(Boolean, default=False)
    missing_mask        = Column(Boolean, default=False)

    notes               = Column(Text, nullable=True)
    verified_by         = Column(String(100), nullable=True)
    verified_at         = Column(DateTime(timezone=True), nullable=True)
    status              = Column(Enum(ViolationStatus), default=ViolationStatus.VERIFIED)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    capture   = relationship("Capture", back_populates="violations")
    detection = relationship("Detection", back_populates="violations")  # ← pastikan back_populates="violations"
    worker    = relationship("Worker", back_populates="violations")