"""Skrip uji koneksi PostgreSQL untuk project Deteksi Tanaman Melon.

Jalankan dari folder backend/:
    python test_connection.py
"""

import sys

from sqlalchemy import text

from app.config import settings
from app.db.database import engine


def test_connection() -> bool:
    """Menguji koneksi ke PostgreSQL dan menampilkan informasi server.

    Returns:
        bool: True jika koneksi berhasil, False jika gagal.
    """
    print(f"Menguji koneksi ke database: {settings.DB_NAME}")
    print(f"Host: {settings.DB_HOST}:{settings.DB_PORT}")
    print("-" * 50)

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.scalar() == 1:
                version: str = connection.execute(
                    text("SELECT version()")
                ).scalar_one()
                print("[OK] Koneksi PostgreSQL BERHASIL")
                print(f"[OK] Versi server: {version}")
                return True
            print("[GAGAL] Query pengujian tidak mengembalikan hasil valid.")
            return False
    except Exception as exc:  # noqa: BLE001
        print("[GAGAL] Koneksi PostgreSQL GAGAL")
        print(f"Detail error: {exc}")
        return False


if __name__ == "__main__":
    sys.exit(0 if test_connection() else 1)