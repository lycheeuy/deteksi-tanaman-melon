"""Detection Service: pipeline AI lengkap Deteksi Tanaman Melon.

Menggabungkan PredictionService (inferensi mentah) dengan FOMODecoder
(decoding grid) menjadi satu hasil deteksi terstruktur, termasuk
dequantization output INT8. Tidak memanggil TensorFlow Lite secara
langsung (SRP).
"""

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

from app.ai.fomo_decoder import FOMODecoder
from app.services.prediction_service import PredictionService

logger = logging.getLogger(__name__)


class DetectionService:
    """Service utama: gambar -> inferensi -> dequantize -> decode."""

    def __init__(
        self,
        threshold: float = 0.5,
        background_class_index: int = 0,
    ) -> None:
        """Menginisialisasi PredictionService dan FOMODecoder.

        Args:
            threshold: Ambang confidence decoder (default 0.5).
            background_class_index: Indeks channel background pada
                output model. Default 0 sesuai konvensi Edge Impulse
                FOMO (background selalu di channel pertama).

        Raises:
            FileNotFoundError: Jika file model tidak ditemukan.
            RuntimeError: Jika model gagal dimuat.
            ValueError: Jika threshold di luar rentang 0..1.
        """
        self.prediction_service: PredictionService = PredictionService()
        self.decoder: FOMODecoder = FOMODecoder(
            threshold=threshold,
            background_class_index=background_class_index,
        )
        logger.info("DetectionService siap digunakan.")

    @staticmethod
    def _dequantize(
        tensor: np.ndarray, output_detail: dict[str, Any]
    ) -> np.ndarray:
        """Mengubah tensor INT8/UINT8 quantized menjadi float32.

        Rumus TFLite: real_value = scale * (quantized - zero_point).
        Tensor float dikembalikan apa adanya.

        Args:
            tensor: Output mentah dari interpreter.
            output_detail: Entri output_details TFLite yang memuat
                parameter kuantisasi (scale, zero_point).

        Returns:
            np.ndarray: Tensor float32 (probabilitas 0..1 untuk FOMO).
        """
        if tensor.dtype not in (np.int8, np.uint8):
            return tensor.astype(np.float32)

        scale, zero_point = output_detail.get("quantization", (0.0, 0))
        if scale == 0.0:
            logger.warning(
                "Tensor %s quantized tapi scale=0; dequantization "
                "dilewati.",
                tensor.dtype,
            )
            return tensor.astype(np.float32)

        return (
            tensor.astype(np.float32) - float(zero_point)
        ) * float(scale)

    def _build_result(
        self, raw_output: list[np.ndarray]
    ) -> dict[str, Any]:
        """Dequantize, decode, urutkan, dan susun hasil terstruktur.

        Args:
            raw_output: List output mentah dari PredictionService.

        Returns:
            dict: {"total_detection": int, "detections": list[dict]},
            detections terurut confidence tertinggi lebih dulu.

        Raises:
            ValueError: Jika raw_output kosong atau shape tidak sesuai.
        """
        if not raw_output:
            raise ValueError("raw_output kosong, tidak ada yang di-decode.")

        # Model FOMO memiliki satu output tensor (grid heatmap).
        output_details = self.prediction_service.engine.get_output_details()
        dequantized: np.ndarray = self._dequantize(
            raw_output[0], output_details[0]
        )

        detections: list[dict] = self.decoder.decode(dequantized)

        # Urutkan berdasarkan confidence tertinggi.
        detections.sort(
            key=lambda x: x["confidence"],
            reverse=True,
        )

        return {
            "total_detection": len(detections),
            "detections": detections,
        }

    def detect_image(self, image_path: str | Path) -> dict[str, Any]:
        """Menjalankan pipeline deteksi lengkap dari file gambar.

        Alur: PredictionService.predict_image() -> dequantize
        raw_output -> FOMODecoder.decode() -> urutkan -> hasil.

        Args:
            image_path: Path menuju file gambar.

        Returns:
            dict: {"image_path": str, "total_detection": int,
            "detections": [{"class_id", "label", "confidence",
            "grid_x", "grid_y"}, ...]} terurut confidence menurun.

        Raises:
            FileNotFoundError: Jika file gambar tidak ditemukan.
            ValueError: Jika file bukan gambar valid atau output kosong.
            RuntimeError: Jika inferensi gagal.
        """
        try:
            start = time.perf_counter()
            prediction = self.prediction_service.predict_image(image_path)
            elapsed = time.perf_counter() - start

            result = self._build_result(prediction["raw_output"])
            result["image_path"] = str(image_path)

            logger.info(
                "Deteksi selesai | image_path=%s | total_detection=%d | "
                "inference_time=%.3f sec",
                image_path,
                result["total_detection"],
                elapsed,
            )
            return result
        except Exception:
            logger.error(
                "Deteksi gagal untuk file: %s", image_path, exc_info=True
            )
            raise

    def detect_numpy(self, image: np.ndarray) -> dict[str, Any]:
        """Menjalankan pipeline deteksi lengkap dari numpy array (BGR).

        Args:
            image: Gambar mentah BGR (mis. frame dari ESP32-CAM).

        Returns:
            dict: {"total_detection": int, "detections": [...]}
            (tanpa image_path), terurut confidence menurun.

        Raises:
            ValueError: Jika gambar tidak valid atau output kosong.
            RuntimeError: Jika inferensi gagal.
        """
        try:
            start = time.perf_counter()
            prediction = self.prediction_service.predict_numpy(image)
            elapsed = time.perf_counter() - start

            result = self._build_result(prediction["raw_output"])

            logger.info(
                "Deteksi selesai | sumber=numpy | total_detection=%d | "
                "inference_time=%.3f sec",
                result["total_detection"],
                elapsed,
            )
            return result
        except Exception:
            logger.error("Deteksi dari numpy array gagal.", exc_info=True)
            raise