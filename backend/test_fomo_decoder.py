"""Skrip pengujian FOMODecoder dengan tensor dummy.

Jalankan dari folder backend/:
    python test_fomo_decoder.py
"""

import sys

import numpy as np

from app.ai.fomo_decoder import FOMODecoder


def build_dummy_tensor() -> np.ndarray:
    """Membuat tensor dummy (1, 12, 12, 6) dengan beberapa deteksi kuat.

    Returns:
        np.ndarray: Tensor logits dengan 3 cell ber-confidence tinggi
        dan 1 cell background kuat (harus diabaikan decoder).
    """
    rng = np.random.default_rng(seed=42)
    # Noise kecil sebagai latar; background (channel terakhir) dominan
    # tipis di seluruh grid agar cell biasa tidak lolos threshold.
    tensor = rng.normal(loc=0.0, scale=0.1, size=(1, 12, 12, 6)).astype(
        np.float32
    )
    tensor[0, :, :, 5] += 1.0  # background unggul tipis di semua cell

    # Deteksi kuat yang diharapkan lolos:
    tensor[0, 2, 3, 0] = 8.0   # class 0 di grid (x=3, y=2)
    tensor[0, 7, 7, 2] = 9.0   # class 2 di grid (x=7, y=7)
    tensor[0, 10, 1, 4] = 7.5  # class 4 di grid (x=1, y=10)

    # Cell dengan background sangat kuat (harus diabaikan):
    tensor[0, 5, 5, 5] = 10.0

    return tensor


def main() -> int:
    """Menjalankan pengujian decoder."""
    print("[1] Generate tensor dummy shape (1, 12, 12, 6) ...")
    tensor = build_dummy_tensor()
    print(f"    Shape: {tensor.shape}, dtype: {tensor.dtype}")

    print("[2] Menjalankan FOMODecoder.decode() (threshold 0.5) ...")
    decoder = FOMODecoder(threshold=0.5)

    try:
        detections = decoder.decode(tensor)
    except Exception as exc:  # noqa: BLE001
        print("\n[GAGAL] Decoding GAGAL")
        print(f"Detail error: {exc}")
        return 1

    print(f"\n=== HASIL DECODE (jumlah deteksi: {len(detections)}) ===")
    for det in detections:
        print(
            f"    class_id={det['class_id']} | "
            f"confidence={det['confidence']:.4f} | "
            f"grid_x={det['grid_x']} | grid_y={det['grid_y']}"
        )

    # Verifikasi sesuai skenario dummy.
    expected = {(3, 2, 0), (7, 7, 2), (1, 10, 4)}
    found = {
        (det["grid_x"], det["grid_y"], det["class_id"])
        for det in detections
    }
    assert expected == found, (
        f"Deteksi tidak sesuai harapan. Diharapkan {expected}, "
        f"ditemukan {found}"
    )
    assert all(det["confidence"] >= 0.5 for det in detections)

    print("\n[OK] Pengujian FOMODecoder BERHASIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())