"""
Router untuk manajemen data pekerja.
Pengawas K3 / admin bisa tambah dan lihat daftar pekerja.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.worker import Worker
from app.schemas.worker import WorkerCreate, WorkerResponse

router = APIRouter(prefix="/api/workers", tags=["Workers"])


@router.post("/", response_model=WorkerResponse, summary="Tambah pekerja baru")
def create_worker(worker_data: WorkerCreate, db: Session = Depends(get_db)):
    """
    Tambah data pekerja baru ke database.
    Dipakai pengawas untuk mendaftarkan pekerja sebelum bisa dipilih saat input pelanggaran.
    """
    # Cek apakah employee_id sudah ada (jika diisi)
    if worker_data.employee_id:
        existing = db.query(Worker).filter(Worker.employee_id == worker_data.employee_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Employee ID sudah terdaftar")

    new_worker = Worker(**worker_data.model_dump())
    db.add(new_worker)
    db.commit()
    db.refresh(new_worker)
    return new_worker


@router.get("/", response_model=List[WorkerResponse], summary="Ambil semua data pekerja")
def get_workers(db: Session = Depends(get_db)):
    """Ambil daftar semua pekerja. Dipakai saat pengawas mau pilih siapa pelanggarnya."""
    return db.query(Worker).all()


@router.get("/{worker_id}", response_model=WorkerResponse, summary="Ambil data pekerja by ID")
def get_worker(worker_id: int, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Pekerja tidak ditemukan")
    return worker
