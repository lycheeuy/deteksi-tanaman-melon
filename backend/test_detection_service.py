"""Skrip pengujian DetectionService (pipeline AI lengkap).

Jalankan dari folder backend/:
    python test_detection_service.py [path_gambar_opsional]

Jika path gambar tidak diberikan, skrip membuat gambar sample sintetis
otomatis. Untuk hasil bermakna, gunakan foto tanaman melon asli.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from app.services.detection_service import DetectionService

SAMPLE_PATH = Path("output_test/sample_detection.jpg")


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
    """Menjalankan pengujian pipeline deteksi lengkap."""
    try:
        print("[1] Inisialisasi DetectionService (load model) ...")
        service = DetectionService(threshold=0.5)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print("\n[GAGAL] DetectionService tidak berhasil diinisialisasi")
        print(f"Detail error: {exc}")
        return 1

    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1])
        print(f"[2] Menggunakan gambar dari argumen: {image_path}")
    else:
        print("[2] Menyiapkan gambar sample ...")
        image_path = ensure_sample_image()

    try:
        print("[3] Menjalankan detect_image() ...")
        result = service.detect_image(image_path)
    except Exception as exc:  # noqa: BLE001
        print("\n[GAGAL] Deteksi GAGAL")
        print(f"Detail error: {exc}")
        return 1

    print("\n=== HASIL DETEKSI ===")
    print(f"    Jumlah deteksi: {result['total_detection']}")
    for det in result["detections"]:
        print(
            f"    - label={det['label']!r} | "
            f"confidence={det['confidence']:.4f} | "
            f"grid_x={det['grid_x']} | grid_y={det['grid_y']}"
        )

    if result["total_detection"] == 0:
        print(
            "    (Tidak ada objek terdeteksi — wajar untuk gambar "
            "sintetis. Coba dengan foto tanaman melon asli.)"
        )

    print("\n[OK] Pengujian DetectionService BERHASIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())