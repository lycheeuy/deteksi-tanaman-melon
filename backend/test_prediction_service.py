"""Skrip pengujian PredictionService (inferensi mentah end-to-end).

Jalankan dari folder backend/:
    python test_prediction_service.py [path_gambar_opsional]

Jika path gambar tidak diberikan, skrip membuat gambar sample sintetis
otomatis.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from app.services.prediction_service import PredictionService

SAMPLE_PATH = Path("output_test/sample_prediction.jpg")


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
    """Menjalankan pengujian inferensi mentah."""
    try:
        print("[1] Inisialisasi PredictionService (load model) ...")
        service = PredictionService()
    except (FileNotFoundError, RuntimeError) as exc:
        print("\n[GAGAL] Model tidak berhasil dimuat")
        print(f"Detail error: {exc}")
        return 1

    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1])
        print(f"[2] Menggunakan gambar dari argumen: {image_path}")
    else:
        print("[2] Menyiapkan gambar sample ...")
        image_path = ensure_sample_image()

    try:
        print("[3] Menjalankan predict_image() ...")
        result = service.predict_image(image_path)

        print("\n=== HASIL INFERENSI MENTAH ===")
        print(f"    input shape  : {result['input_shape']}")
        print(f"    output shape : {result['output_shape']}")
        for i, out in enumerate(result["raw_output"]):
            print(f"    output[{i}] dtype : {out.dtype}")
            print(f"    output[{i}] min   : {out.min()}")
            print(f"    output[{i}] max   : {out.max()}")

        print("\n[OK] Pengujian PredictionService BERHASIL")
        return 0
    except Exception as exc:  # noqa: BLE001
        print("\n[GAGAL] Pengujian PredictionService GAGAL")
        print(f"Detail error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())