"""Skrip pengujian AnnotationService (deteksi -> anotasi -> cek file).

Jalankan dari folder backend/:
    python test_annotation_service.py [path_gambar_opsional]

Membutuhkan MODEL_PATH valid di .env (untuk DetectionService).
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from app.services.annotation_service import AnnotationService
from app.services.detection_service import DetectionService

SAMPLE_PATH = Path("output_test/sample_annotation.jpg")


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
    """Menjalankan pengujian anotasi end-to-end."""
    # [1] Siapkan gambar.
    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1])
        print(f"[1] Menggunakan gambar dari argumen: {image_path}")
    else:
        print("[1] Menyiapkan gambar sample ...")
        image_path = ensure_sample_image()

    # [2] Jalankan DetectionService.
    try:
        print("[2] Menjalankan DetectionService ...")
        detection_service = DetectionService()
        result = detection_service.detect_image(image_path)
    except Exception as exc:  # noqa: BLE001
        print("\n[GAGAL] DetectionService gagal")
        print(f"Detail error: {exc}")
        return 1

    # [3] Jalankan AnnotationService.
    try:
        print("[3] Menjalankan AnnotationService ...")
        annotation_service = AnnotationService()
        output_path = annotation_service.annotate_image(
            str(image_path), result["detections"]
        )
    except Exception as exc:  # noqa: BLE001
        print("\n[GAGAL] AnnotationService gagal")
        print(f"Detail error: {exc}")
        return 1

    # [4] Cek file hasil.
    print("[4] Memeriksa file hasil ...")
    output_file = Path(output_path)
    assert output_file.is_file(), "File anotasi tidak ditemukan!"
    assert output_file.parent.name == "annotated"
    assert output_file.name.endswith("_annotated.jpg")

    # [5] Ringkasan.
    print("\n=== RINGKASAN ===")
    print(f"    Input image    : {image_path}")
    print(f"    Output image   : {output_path}")
    print(f"    Jumlah deteksi : {result['total_detection']}")
    print(f"    Lokasi file    : {output_file.resolve()}")

    if result["total_detection"] == 0:
        print(
            "    (Tidak ada deteksi — gambar tersimpan tanpa kotak. "
            "Coba foto tanaman asli untuk melihat anotasi.)"
        )

    print("\n[OK] Pengujian AnnotationService BERHASIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())