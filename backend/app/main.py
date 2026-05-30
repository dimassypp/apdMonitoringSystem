"""
APD Monitoring System - Backend API
Capstone Project - Universitas Brawijaya 2026
Tim: Seronoknya Capstone

Entry point aplikasi FastAPI.
Jalankan dengan: uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.models import worker, capture, detection, violation
from app.database import Base
from app.routers import workers, captures, detections, violations, stream   # ← tambah stream

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="APD Monitoring System API",
    description="""
## Backend API untuk Sistem Monitoring Kepatuhan APD

Sistem ini mendukung transformasi Safety 4.0 di lingkungan manufaktur EPSON
dengan memanfaatkan Computer Vision untuk mendeteksi kepatuhan penggunaan APD.

### Alur Sistem:
1. **Upload Foto** - Foto dari CCTV diupload via `POST /api/captures/upload`
2. **Auto-Enhance** - Foto otomatis diperjelas setelah upload
3. **Deteksi AI** - Modul AI menganalisis foto dan mengirim hasilnya ke `POST /api/detections/report`
4. **Verifikasi** - Pengawas K3 verifikasi via `PATCH /api/detections/{id}/verify`
5. **Dashboard** - Data pelanggaran dapat diambil via `GET /api/violations/`
6. **Live Stream** - Kamera langsung via `GET /api/stream/video`

### Tim Pengembang:
- **Dimas Yoga Pratama** - Backend & Integration
- **Favian Igneusa Apta** - System Analyst
- **Qudwa Abyan Ghiffara** - AI/ML Engineer
- **Hanna Lailatul Islamiyah** - Embedded System & Hardware
- **Dayinta Raras Apsari** - System Optimization Engineer
    """,
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workers.router)
app.include_router(captures.router)
app.include_router(detections.router)
app.include_router(violations.router)
app.include_router(stream.router)          # ← tambah stream


@app.get("/", tags=["Root"])
def root():
    return {
        "status":     "ok",
        "message":    "APD Monitoring System API is running",
        "docs":       "/docs",
        "stream":     "/api/stream/video",
        "stream_status": "/api/stream/status",
    }