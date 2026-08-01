"""Skrip pengujian endpoint POST /detect dengan FastAPI TestClient.

Jalankan dari folder backend/:
    python test_api_detect.py

Membutuhkan: MODEL_PATH valid, PostgreSQL aktif, dan package httpx
(pip install httpx) untuk TestClient.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def build_sample_jpeg() -> bytes:
    """Membuat gambar sample sintetis sebagai bytes JPEG."""
    height, width = 480, 640
    sample = np.zeros((height, width, 3), dtype=np.uint8)
    for row in range(height):
        sample[row, :] = (40, int(80 + 175 * row / height), 60)  # BGR
    success, buffer = cv2.imencode(".jpg", sample)
    assert success, "Gagal meng-encode gambar sample"
    return buffer.tobytes()


def main() -> int:
    """Menjalankan pengujian endpoint /detect."""
    print("[1] Upload sample image ke POST /detect ...")
    response = client.post(
        "/detect",
        files={"image": ("sample_api.jpg", build_sample_jpeg(), "image/jpeg")},
    )

    print(f"[2] Status code: {response.status_code}")
    assert response.status_code == 200, response.text

    data = response.json()
    print("[3] Memeriksa struktur JSON ...")
    for field in (
        "success",
        "message",
        "record_id",
        "image_path",
        "annotated_image_path",
        "total_detection",
        "detections",
    ):
        assert field in data, f"Field '{field}' tidak ada di response"
    assert data["success"] is True
    assert data["message"] == "Detection completed"
    assert isinstance(data["total_detection"], int)
    assert isinstance(data["detections"], list)
    assert data["total_detection"] == len(data["detections"])

    print("    record_id            :", data["record_id"])
    print("    image_path           :", data["image_path"])
    print("    annotated_image_path :", data["annotated_image_path"])
    print("    total_detection      :", data["total_detection"])

    print("[4] Memastikan file annotated benar-benar dibuat ...")
    annotated = Path(data["annotated_image_path"])
    assert annotated.is_file(), "File annotated tidak ditemukan!"
    assert annotated.parent.name == "annotated"
    print(f"    File ditemukan: {annotated.resolve()}")

    print("[5] Uji kasus gagal: upload kosong (harus 400) ...")
    bad = client.post(
        "/detect", files={"image": ("kosong.jpg", b"", "image/jpeg")}
    )
    print(f"    Status code: {bad.status_code}")
    assert bad.status_code == 400

    print("\n[OK] Pengujian endpoint /detect BERHASIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())