"""Skrip audit path model: memastikan satu sumber konfigurasi.

Jalankan dari folder backend/:
    python check_model_path.py

Memeriksa: (1) tidak ada path .tflite hardcode di kode, (2) nilai
settings.MODEL_PATH, (3) keberadaan file model, (4) lokasi seluruh
file .tflite yang sebenarnya ada di project.
"""

import sys
from pathlib import Path

from app.config import ENV_PATH, settings

BACKEND_DIR = Path(__file__).resolve().parent
FORBIDDEN_PATTERNS = ("models/model.tflite", "app/ai/model.tflite")


def scan_hardcode() -> list[str]:
    """Mencari string path .tflite hardcode di seluruh kode app/."""
    findings: list[str] = []
    for py_file in (BACKEND_DIR / "app").rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        text = py_file.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(pat in line for pat in FORBIDDEN_PATTERNS):
                findings.append(
                    f"{py_file.relative_to(BACKEND_DIR)}:{lineno}: "
                    f"{line.strip()}"
                )
    return findings


def main() -> int:
    print("=" * 60)
    print("[1] SCAN HARDCODE PATH MODEL DI app/")
    findings = scan_hardcode()
    if findings:
        print("    >>> DITEMUKAN hardcode — hapus/salin ulang file ini:")
        for item in findings:
            print(f"    {item}")
    else:
        print("    Bersih. Tidak ada path .tflite hardcode di kode.")
        print("    (Satu-satunya sumber path: settings.MODEL_PATH)")

    print()
    print("[2] NILAI settings.MODEL_PATH (dari .env)")
    print(f"    .env       : {ENV_PATH}")
    print(f"    MODEL_PATH : {settings.MODEL_PATH or '<KOSONG>'}")
    if not settings.MODEL_PATH:
        print("    >>> MODEL_PATH belum diatur di .env.")

    print()
    print("[3] KEBERADAAN FILE MODEL")
    exists = bool(settings.MODEL_PATH) and Path(
        settings.MODEL_PATH
    ).is_file()
    print(f"    Ditemukan  : {exists}")

    print()
    print("[4] SELURUH FILE .tflite DI DALAM backend/")
    tflite_files = [
        p for p in BACKEND_DIR.rglob("*.tflite")
        if ".venv" not in p.parts
    ]
    if not tflite_files:
        print("    Tidak ada file .tflite — salin model Anda dulu.")
    for p in tflite_files:
        rel = p.relative_to(BACKEND_DIR).as_posix()
        print(f"    {rel}")
        if not exists:
            print(f"    >>> Set di .env: MODEL_PATH={rel}")

    print("=" * 60)
    ok = not findings and exists
    print("HASIL:", "SEHAT — jalankan test_history_service.py"
          if ok else "BELUM SEHAT — ikuti petunjuk >>> di atas")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())