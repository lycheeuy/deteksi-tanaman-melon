"""Skrip pengujian ImageService.

Jalankan dari folder backend/:
    python test_image_service.py [path_gambar_opsional]

Jika path gambar tidak diberikan, skrip membuat gambar sample sintetis
secara otomatis sehingga pengujian selalu bisa berjalan.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from app.services.image_service import ImageService

SAMPLE_PATH = Path("output_test/sample_input.jpg")


def ensure_sample_image() -> Path:
    """Membuat gambar sample sintetis jika belum ada gambar dari user."""
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SAMPLE_PATH.is_file():
        # Gradien hijau sederhana 480x640 menyerupai foto daun.
        height, width = 480, 640
        sample = np.zeros((height, width, 3), dtype=np.uint8)
        for row in range(height):
            sample[row, :] = (40, int(80 + 175 * row / height), 60)  # BGR
        cv2.imwrite(str(SAMPLE_PATH), sample)
        print(f"    Gambar sample sintetis dibuat: {SAMPLE_PATH}")
    return SAMPLE_PATH


def main() -> int:
    """Menjalankan seluruh alur pengujian ImageService."""
    service = ImageService()

    # Gunakan path dari argumen jika diberikan, selain itu pakai sample.
    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1])
        print(f"[1] Membaca gambar dari argumen: {image_path}")
    else:
        print("[1] Menyiapkan gambar sample ...")
        image_path = ensure_sample_image()

    try:
        image = service.load_image(image_path)
        print(f"[2] Shape asli            : {image.shape} "
              f"(dtype: {image.dtype})")

        tensor = service.prepare_input(image)
        print(f"[3] Shape prepare_input() : {tensor.shape} "
              f"(dtype: {tensor.dtype})")
        print(f"    Rentang nilai tensor  : min={tensor.min()}, "
              f"max={tensor.max()}")

        saved = service.save_image(image, "output_test/salinan_sample.jpg")
        print(f"[4] Salinan tersimpan     : {saved}")

        # Verifikasi hasil sesuai spesifikasi model.
        assert tensor.shape == (1, 96, 96, 3), "Shape tensor tidak sesuai"
        assert tensor.dtype == np.int8, "Dtype tensor harus int8"
        assert saved.is_file(), "File salinan tidak ditemukan"

        print("\n[OK] Pengujian ImageService BERHASIL")
        return 0
    except Exception as exc:  # noqa: BLE001
        print("\n[GAGAL] Pengujian ImageService GAGAL")
        print(f"Detail error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())