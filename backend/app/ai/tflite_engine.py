"""Engine TensorFlow Lite untuk model MobileNetV2 FOMO (singleton).

Bertanggung jawab hanya untuk memuat model .tflite dan menjalankan
inferensi mentah. Preprocessing dan postprocessing berada di luar
tanggung jawab class ini (SRP).
"""

import logging
from typing import Any

import numpy as np
import tensorflow as tf

from app.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


class TFLiteEngine:
    """Singleton pembungkus tensorflow.lite.Interpreter.

    Model hanya di-load satu kali selama lifetime proses. Pemanggilan
    TFLiteEngine() berikutnya mengembalikan instance yang sama.
    """

    _instance: "TFLiteEngine | None" = None

    def __new__(cls) -> "TFLiteEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Cegah re-inisialisasi saat singleton dipanggil berulang.
        if getattr(self, "_initialized", False):
            return
        self._initialized: bool = True

        self.model_path: str = settings.MODEL_PATH
        self.interpreter: tf.lite.Interpreter | None = None
        self.input_details: list[dict[str, Any]] | None = None
        self.output_details: list[dict[str, Any]] | None = None

    def load_model(self) -> None:
        """Memuat model .tflite dan mengalokasikan tensor (sekali saja).

        Raises:
            FileNotFoundError: Jika file model tidak ditemukan.
            RuntimeError: Jika model gagal dimuat atau dialokasikan.
        """
        if self.interpreter is not None:
            logger.info("Model sudah dimuat sebelumnya, load dilewati.")
            return

        if not self.model_path:
            raise FileNotFoundError(
                "MODEL_PATH belum diatur. Tambahkan baris "
                "MODEL_PATH=path/ke/model.tflite pada file backend/.env "
                "(path relatif dihitung dari folder backend/)."
            )

        logger.info("Memuat model TFLite dari: %s", self.model_path)
        try:
            self.interpreter = tf.lite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
        except ValueError as exc:
            self.interpreter = None
            logger.error("File model tidak ditemukan/tidak valid: %s", exc)
            raise FileNotFoundError(
                f"Model tidak ditemukan atau tidak valid: {self.model_path}"
            ) from exc
        except Exception as exc:
            self.interpreter = None
            logger.error("Gagal memuat model TFLite: %s", exc)
            raise RuntimeError(f"Gagal memuat model TFLite: {exc}") from exc

        logger.info("Model TFLite berhasil dimuat dan tensor dialokasikan.")

    def predict(self, image: np.ndarray) -> list[np.ndarray]:
        """Menjalankan inferensi dan mengembalikan output mentah model.

        Tidak melakukan preprocessing maupun postprocessing. Input harus
        sudah sesuai shape dan dtype yang diminta model.

        Args:
            image: Tensor input siap-pakai (mis. shape [1, H, W, 3]).

        Returns:
            list[np.ndarray]: Output mentah untuk setiap output tensor.

        Raises:
            RuntimeError: Jika model belum dimuat atau inferensi gagal.
        """
        if (
            self.interpreter is None
            or self.input_details is None
            or self.output_details is None
        ):
            raise RuntimeError(
                "Model belum dimuat. Panggil load_model() terlebih dahulu."
            )

        try:
            self.interpreter.set_tensor(
                self.input_details[0]["index"], image
            )
            self.interpreter.invoke()
            outputs: list[np.ndarray] = [
                self.interpreter.get_tensor(detail["index"])
                for detail in self.output_details
            ]
        except Exception as exc:
            logger.error("Inferensi gagal: %s", exc)
            raise RuntimeError(f"Inferensi TFLite gagal: {exc}") from exc

        return outputs

    def get_input_details(self) -> list[dict[str, Any]]:
        """Mengembalikan detail input tensor model.

        Raises:
            RuntimeError: Jika model belum dimuat.
        """
        if self.input_details is None:
            raise RuntimeError(
                "Model belum dimuat. Panggil load_model() terlebih dahulu."
            )
        return self.input_details

    def get_output_details(self) -> list[dict[str, Any]]:
        """Mengembalikan detail output tensor model.

        Raises:
            RuntimeError: Jika model belum dimuat.
        """
        if self.output_details is None:
            raise RuntimeError(
                "Model belum dimuat. Panggil load_model() terlebih dahulu."
            )
        return self.output_details