"""Skrip pengujian HistoryService (deteksi -> simpan -> query kembali).

Jalankan dari folder backend/:
    python test_history_service.py [path_gambar_opsional]

Membutuhkan PostgreSQL aktif dan MODEL_PATH valid di .env.
"""

import sys
import uuid
from pathlib import Path

import cv2
import numpy as np

from app.services.history_service import HistoryService

SAMPLE_PATH = Path("output_test/sample_history.jpg")


def ensure_sample_image() -> Path:
    """Membuat gambar sample sintetis jika user tidak memberikan path."""
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SAMPLE_PATH.is_file():
        height, width = 480, 640
        sample = np.zeros((height, width, 3), dtype=np.uint8)
        for row in range(height):
            sample[row, :] = (40, int(80 + 175 * row / height), 60)  # BGR
        cv2.imwrite(str(SAMPLE_PATH), sample)
        print(f"    Gambar sample sintetis dibuat: {SAMPLE_PATH}")
    return SAMPLE_PATH


def main() -> int:
    """Menjalankan pengujian simpan riwayat deteksi."""
    try:
        print("[1] Inisialisasi HistoryService (load model) ...")
        service = HistoryService()
    except (FileNotFoundError, RuntimeError) as exc:
        print("\n[GAGAL] HistoryService tidak berhasil diinisialisasi")
        print(f"Detail error: {exc}")
        return 1

    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1])
        print(f"[2] Menggunakan gambar dari argumen: {image_path}")
    else:
        print("[2] Menyiapkan gambar sample ...")
        image_path = ensure_sample_image()

    try:
        print("[3] Menjalankan save_detection() ...")
        saved = service.save_detection(str(image_path))

        confidence = saved["confidence"]
        print("\n=== HASIL PENYIMPANAN ===")
        print(f"    Record ID  : {saved['record_id']}")
        print(f"    Label      : {saved['result']['label']}")
        print(
            "    Confidence : "
            + (f"{confidence:.4f}" if confidence is not None else "-")
        )
        print(f"    Image Path : {saved['result']['image_path']}")

        print("\n[4] Query kembali database untuk verifikasi ...")
        record_id = uuid.UUID(saved["record_id"])
        fetched = service.get_history_by_id(record_id)

        assert saved["saved"] is True
        assert fetched is not None, "Record tidak ditemukan di database!"
        assert str(fetched["id"]) == saved["record_id"]
        assert fetched["label"] == saved["result"]["label"]
        assert fetched["image_path"] == str(image_path)

        print("    Record ditemukan kembali di database:")
        print(f"    id={fetched['id']}")
        print(f"    label={fetched['label']!r} | action={fetched['action']!r}")
        print(f"    created_at={fetched['created_at']}")

        print("\n[OK] Pengujian HistoryService BERHASIL — data tersimpan")
        return 0
    except Exception as exc:  # noqa: BLE001
        print("\n[GAGAL] Pengujian HistoryService GAGAL")
        print(f"Detail error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())