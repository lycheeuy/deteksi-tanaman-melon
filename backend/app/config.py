"""Konfigurasi aplikasi Deteksi Tanaman Melon.

Membaca seluruh konfigurasi dari file .env menggunakan python-dotenv.
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Muat .env dengan path EKSPLISIT relatif terhadap file ini
# (backend/.env), sehingga tidak bergantung pada working directory
# maupun cara skrip dijalankan (terminal, debugger VS Code, uvicorn,
# systemd di VPS).
ENV_PATH: Path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True, encoding="utf-8")


class Settings:
    """Menampung seluruh konfigurasi aplikasi dari environment variables."""

    def __init__(self) -> None:
        # Aplikasi
        self.APP_NAME: str = os.getenv("APP_NAME", "Deteksi Tanaman Melon")
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        # Waktu build/deploy (diisi pipeline deploy; kosong = fallback
        # ke waktu proses start pada endpoint /monitor).
        self.BUILD_TIME: str = os.getenv("BUILD_TIME", "")
        self.DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

        # Database
        self.DB_HOST: str = os.getenv("DB_HOST", "localhost")
        self.DB_PORT: str = os.getenv("DB_PORT", "5432")
        self.DB_USER: str = os.getenv("DB_USER", "postgres")
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
        self.DB_NAME: str = os.getenv("DB_NAME", "deteksi_melon")

        # Autentikasi JWT. WAJIB ganti SECRET_KEY di production.
        self.SECRET_KEY: str = os.getenv(
            "SECRET_KEY", "dev-secret-ganti-di-production"
        )
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
        )

        # Alamat ESP32-CAM (mis. http://192.168.1.50). Opsional; fitur
        # live camera menolak dengan pesan jelas bila kosong.
        self.ESP32_URL: str = os.getenv("ESP32_URL", "").rstrip("/")

        # Model AI. WAJIB diatur lewat .env (tidak ada default hardcode).
        # Path relatif diselesaikan terhadap folder backend/ (lokasi
        # .env), bukan working directory, agar konsisten dari terminal,
        # debugger, maupun systemd/uvicorn.
        _raw_model_path: str = os.getenv("MODEL_PATH", "")
        if _raw_model_path:
            _model_path = Path(_raw_model_path)
            if not _model_path.is_absolute():
                _model_path = ENV_PATH.parent / _model_path
            self.MODEL_PATH: str = str(_model_path)
        else:
            self.MODEL_PATH = ""

    @property
    def DATABASE_URL(self) -> str:
        """Menyusun URL koneksi PostgreSQL untuk SQLAlchemy."""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    """Mengembalikan instance Settings tunggal (cached)."""
    return Settings()


settings: Settings = get_settings()