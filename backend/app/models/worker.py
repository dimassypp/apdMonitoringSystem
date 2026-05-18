from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Worker(Base):
    """
    Tabel pekerja produksi EPSON.
    Data ini diinput manual oleh pengawas K3 atau admin.
    """
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)           # Nama lengkap pekerja
    employee_id = Column(String(50), unique=True, nullable=True)  # ID karyawan (opsional)
    department = Column(String(100), nullable=True)      # Area kerja / departemen
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi: satu pekerja bisa punya banyak catatan pelanggaran
    violations = relationship("Violation", back_populates="worker")
