"""Prediction Service: menghubungkan ImageService dengan TFLiteEngine.

Bertugas hanya menjalankan inferensi dan mengembalikan output mentah
model. Decoding FOMO, bounding box, label mapping, dan postprocessing
lain berada di luar tanggung jawab class ini (SRP).
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np

from app.ai.tflite_engine import TFLiteEngine
from app.services.image_service import ImageService

logger = logging.getLogger(__name__)


class PredictionService:
    """Orkestrasi pipeline: gambar -> tensor input -> inferensi mentah."""

    def __init__(self) -> None:
        """Menginisialisasi ImageService dan TFLiteEngine, lalu memuat
        model satu kali.

        Raises:
            FileNotFoundError: Jika file model tidak ditemukan.
            RuntimeError: Jika model gagal dimuat.
        """
        self.image_service: ImageService = ImageService()
        self.engine: TFLiteEngine = TFLiteEngine()
        # TFLiteEngine adalah singleton dan load_model() idempoten,
        # sehingga model dijamin hanya dimuat satu kali.
        self.engine.load_model()
        logger.info("PredictionService siap digunakan.")

    def predict_numpy(self, image: np.ndarray) -> dict[str, Any]:
        """Menjalankan inferensi dari gambar numpy (BGR, hasil OpenCV).

        Args:
            image: Gambar mentah BGR (mis. frame dari ESP32-CAM).

        Returns:
            dict: {
                "input_shape": tuple shape tensor input,
                "output_shape": list shape setiap output tensor,
                "raw_output": list numpy.ndarray output mentah model,
            }

        Raises:
            ValueError: Jika gambar tidak valid.
            RuntimeError: Jika inferensi gagal.
        """
        try:
            input_tensor: np.ndarray = self.image_service.prepare_input(image)
            raw_output: list[np.ndarray] = self.engine.predict(input_tensor)
        except Exception:
            logger.error("Inferensi dari numpy array gagal.", exc_info=True)
            raise

        result: dict[str, Any] = {
            "input_shape": tuple(input_tensor.shape),
            "output_shape": [tuple(out.shape) for out in raw_output],
            "raw_output": raw_output,
        }
        logger.info(
            "Inferensi selesai. input=%s, output=%s",
            result["input_shape"],
            result["output_shape"],
        )
        return result

    def predict_image(self, image_path: str | Path) -> dict[str, Any]:
        """Menjalankan inferensi dari file gambar di disk.

        Args:
            image_path: Path menuju file gambar.

        Returns:
            dict: Sama seperti predict_numpy() — input_shape,
            output_shape, dan raw_output mentah model.

        Raises:
            FileNotFoundError: Jika file gambar tidak ditemukan.
            ValueError: Jika file gagal dibaca sebagai gambar.
            RuntimeError: Jika inferensi gagal.
        """
        logger.info("Menjalankan prediksi untuk file: %s", image_path)
        image: np.ndarray = self.image_service.load_image(image_path)
        return self.predict_numpy(image)