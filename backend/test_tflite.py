"""Skrip pengujian TFLiteEngine (load model, tanpa prediksi gambar).

Jalankan dari folder backend/:
    python test_tflite.py
"""

import sys

from app.ai.tflite_engine import TFLiteEngine
from app.config import settings


def main() -> int:
    """Memuat model dan menampilkan detail input/output."""
    print(f"[1] Memuat model dari: {settings.MODEL_PATH}")
    engine = TFLiteEngine()

    try:
        engine.load_model()
    except (FileNotFoundError, RuntimeError) as exc:
        print("\n[GAGAL] Model tidak berhasil dimuat")
        print(f"Detail error: {exc}")
        return 1

    print("\n[2] Input details:")
    for detail in engine.get_input_details():
        print(f"    name  : {detail['name']}")
        print(f"    shape : {detail['shape']}")
        print(f"    dtype : {detail['dtype']}")
        print("-" * 50)

    print("[3] Output details:")
    for detail in engine.get_output_details():
        print(f"    name  : {detail['name']}")
        print(f"    shape : {detail['shape']}")
        print(f"    dtype : {detail['dtype']}")
        print("-" * 50)

    print("[4] Verifikasi singleton ...")
    second = TFLiteEngine()
    print(f"    Instance sama: {engine is second}")
    second.load_model()  # Harus tercatat "load dilewati" di log

    print("\n[OK] Model TFLite BERHASIL dimuat")
    return 0


if __name__ == "__main__":
    sys.exit(main())