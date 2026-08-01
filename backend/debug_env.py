"""Skrip diagnosis konfigurasi .env dan koneksi database.

Jalankan dari folder backend/:
    python debug_env.py

Memeriksa: keberadaan .env, encoding file, hasil parsing dotenv,
environment variable, nilai Settings, dan uji koneksi langsung.
Password tidak pernah ditampilkan utuh (hanya panjang karakternya).
"""

import os
import sys

# Periksa environment SEBELUM load_dotenv dipanggil oleh config.
_PRELOAD_DB_PASSWORD = os.environ.get("DB_PASSWORD")

from dotenv import dotenv_values  # noqa: E402

from app.config import ENV_PATH, settings  # noqa: E402


def mask(value: str | None) -> str:
    """Menampilkan status nilai tanpa membocorkan isinya."""
    if value is None:
        return "<tidak ada>"
    if value == "":
        return "<STRING KOSONG>"
    return f"<terisi, {len(value)} karakter>"


def main() -> int:
    print("=" * 60)
    print("[1] FILE .env")
    print(f"    Path yang dicari : {ENV_PATH}")
    print(f"    Ditemukan        : {ENV_PATH.is_file()}")

    if not ENV_PATH.is_file():
        print("\n    >>> AKAR MASALAH: file .env tidak ada di path itu.")
        print("    >>> Buat backend/.env berisi DB_PASSWORD=... dst.")
        return 1

    raw = ENV_PATH.read_bytes()
    head = raw[:4]
    print(f"    Ukuran           : {len(raw)} bytes")
    print(f"    4 byte pertama   : {head.hex(' ')}")
    if head.startswith(b"\xff\xfe") or head.startswith(b"\xfe\xff"):
        print("\n    >>> AKAR MASALAH: file ber-encoding UTF-16")
        print("    >>> (biasanya akibat 'echo' / '>' di PowerShell).")
        print("    >>> python-dotenv gagal mem-parsing-nya secara diam-")
        print("    >>> diam. Buat ulang .env via VS Code (UTF-8).")
        return 1
    if head.startswith(b"\xef\xbb\xbf"):
        print("    Catatan: ada BOM UTF-8 (umumnya masih aman).")

    print()
    print("[2] HASIL PARSING python-dotenv")
    parsed = dotenv_values(ENV_PATH)
    if not parsed:
        print("    >>> AKAR MASALAH: .env ada tapi TIDAK ADA variabel")
        print("    >>> yang berhasil di-parse (format/encoding rusak).")
        return 1
    for key in sorted(parsed):
        shown = mask(parsed[key]) if "PASSWORD" in key else parsed[key]
        print(f"    {key} = {shown}")
    if "DB_PASSWORD" not in parsed:
        print("\n    >>> AKAR MASALAH: tidak ada key DB_PASSWORD di .env")
        print("    >>> (mungkin salah nama, mis. POSTGRES_PASSWORD, atau")
        print("    >>> password ditulis di dalam DATABASE_URL= yang")
        print("    >>> TIDAK dibaca oleh config.py).")

    print()
    print("[3] ENVIRONMENT VARIABLE WINDOWS/SHELL")
    print(f"    DB_PASSWORD sebelum load_dotenv: "
          f"{mask(_PRELOAD_DB_PASSWORD)}")
    if _PRELOAD_DB_PASSWORD == "":
        print("    >>> AKAR MASALAH: shell/OS men-set DB_PASSWORD kosong;")
        print("    >>> load_dotenv default TIDAK menimpanya.")

    print()
    print("[4] NILAI AKHIR settings")
    print(f"    DB_HOST     = {settings.DB_HOST}")
    print(f"    DB_PORT     = {settings.DB_PORT}")
    print(f"    DB_USER     = {settings.DB_USER}")
    print(f"    DB_NAME     = {settings.DB_NAME}")
    print(f"    DB_PASSWORD = {mask(settings.DB_PASSWORD)}")

    if not settings.DB_PASSWORD:
        print("\n    >>> DB_PASSWORD KOSONG — inilah sumber fe_sendauth.")
        print("    >>> Perbaiki sesuai temuan [1]-[3] di atas.")
        return 1

    print()
    print("[5] UJI KONEKSI LANGSUNG")
    from sqlalchemy import text
    from app.db.database import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("    Koneksi BERHASIL — konfigurasi sudah sehat.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"    Koneksi GAGAL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())