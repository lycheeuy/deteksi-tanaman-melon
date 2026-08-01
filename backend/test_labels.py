"""Skrip pengujian label mapping dan integrasinya dengan FOMODecoder.

Jalankan dari folder backend/:
    python test_labels.py
"""

import sys

import numpy as np

from app.ai.fomo_decoder import FOMODecoder
from app.ai.labels import LABELS, get_label


def build_dummy_tensor() -> np.ndarray:
    """Membuat tensor dummy (1, 12, 12, 6) dengan 3 deteksi kuat."""
    rng = np.random.default_rng(seed=42)
    tensor = rng.normal(loc=0.0, scale=0.1, size=(1, 12, 12, 6)).astype(
        np.float32
    )
    tensor[0, :, :, 5] += 1.0   # background (channel terakhir)
    tensor[0, 2, 3, 0] = 8.0    # Daun Siap Pangkas
    tensor[0, 7, 7, 2] = 9.0    # Buah Siap Panen
    tensor[0, 10, 1, 4] = 7.5   # Tunas Air
    return tensor


def main() -> int:
    """Menjalankan seluruh pengujian label mapping."""
    print("[1] Seluruh mapping LABELS:")
    for class_id, label in LABELS.items():
        print(f"    {class_id} -> {label}")

    print("\n[2] Pengujian get_label() ...")
    assert get_label(0) == "Daun Siap Pangkas"
    assert get_label(2) == "Buah Siap Panen"
    assert get_label(4) == "Tunas Air"
    print("    get_label(0)  ->", get_label(0))
    print("    get_label(4)  ->", get_label(4))

    # class_id di luar mapping harus mengembalikan "Unknown".
    assert get_label(99) == "Unknown"
    assert get_label(-1) == "Unknown"
    print("    get_label(99) ->", get_label(99))

    print("\n[3] Menjalankan FOMODecoder dengan dummy tensor ...")
    decoder = FOMODecoder(threshold=0.5)
    detections = decoder.decode(build_dummy_tensor())

    print(f"\n=== HASIL DECODE (jumlah deteksi: {len(detections)}) ===")
    for det in detections:
        print(
            f"    class_id={det['class_id']} | "
            f"label={det['label']!r} | "
            f"confidence={det['confidence']:.4f} | "
            f"grid=({det['grid_x']}, {det['grid_y']})"
        )

    print("\n[4] Verifikasi field 'label' pada seluruh output ...")
    assert len(detections) == 3, "Jumlah deteksi tidak sesuai"
    for det in detections:
        assert "label" in det, "Field 'label' tidak ditemukan"
        assert det["label"] == get_label(det["class_id"])
    print("    Seluruh deteksi memiliki field 'label' yang konsisten.")

    print("\n[OK] Pengujian Label Mapping BERHASIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())