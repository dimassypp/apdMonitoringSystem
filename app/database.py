import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/apd_monitoring")

# Engine = koneksi ke database PostgreSQL
engine = create_engine(DATABASE_URL)

# SessionLocal = factory untuk membuat sesi database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = parent class untuk semua model tabel
Base = declarative_base()


def get_db():
    """
    Dependency function untuk FastAPI.
    Setiap request akan dapat sesi database sendiri,
    dan sesi akan ditutup otomatis setelah request selesai.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
