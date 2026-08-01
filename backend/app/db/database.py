"""Inisialisasi engine SQLAlchemy 2.x untuk koneksi PostgreSQL."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import settings

engine: Engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Validasi koneksi sebelum digunakan dari pool
    future=True,         # Gaya API SQLAlchemy 2.x
    echo=settings.DEBUG, # Log SQL saat mode debug
)