"""Image Service: membaca, memvalidasi, dan menyiapkan gambar untuk
TFLite Engine.

Hanya menangani operasi gambar (SRP). Inferensi AI, bounding box, dan
postprocessing berada di luar tanggung jawab class ini.
"""

from pathlib import Path

import cv2
import numpy as np


class ImageService:
    """Layanan operasi gambar untuk pipeline Deteksi Tanaman Melon."""

    def load_image(self, image_path: str | Path) -> np.ndarray:
        """Membaca gambar dari disk menggunakan OpenCV.

        Args:
            image_path: Path menuju file gambar.

        Returns:
            np.ndarray: Gambar dalam format BGR (default OpenCV).

        Raises:
            FileNotFoundError: Jika file tidak ditemukan.
            ValueError: Jika file ada tapi gagal dibaca sebagai gambar.
        """
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"File gambar tidak ditemukan: {path}")

        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(
                f"File gagal dibaca sebagai gambar (rusak/format tidak "
                f"didukung): {path}"
            )
        return image

    def resize_image(
        self, image: np.ndarray, size: tuple[int, int] = (96, 96)
    ) -> np.ndarray:
        """Mengubah ukuran gambar sesuai ukuran input model.

        Args:
            image: Gambar sumber.
            size: Ukuran tujuan (lebar, tinggi). Default (96, 96).

        Returns:
            np.ndarray: Gambar hasil resize.

        Raises:
            ValueError: Jika input bukan gambar yang valid.
        """
        if image is None or image.size == 0:
            raise ValueError("Gambar kosong, tidak bisa di-resize.")
        return cv2.resize(image, size, interpolation=cv2.INTER_AREA)

    def convert_bgr_to_rgb(self, image: np.ndarray) -> np.ndarray:
        """Mengonversi gambar dari BGR (OpenCV) ke RGB (model).

        Raises:
            ValueError: Jika gambar bukan 3-channel.
        """
        if image is None or image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Gambar harus 3-channel (BGR) untuk konversi.")
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def prepare_input(self, image: np.ndarray) -> np.ndarray:
        """Menyiapkan gambar menjadi tensor input siap-pakai untuk model.

        Tahapan: resize 96x96 -> BGR ke RGB -> kuantisasi ke int8
        (pixel - 128, sesuai zero_point -128 pada model full-integer
        Edge Impulse) -> tambah batch dimension.

        Args:
            image: Gambar BGR hasil load_image().

        Returns:
            np.ndarray: Tensor shape (1, 96, 96, 3), dtype int8.

        Raises:
            ValueError: Jika gambar tidak valid.
        """
        resized = self.resize_image(image, size=(96, 96))
        rgb = self.convert_bgr_to_rgb(resized)

        # Kuantisasi uint8 [0..255] -> int8 [-128..127]. Casting langsung
        # astype(int8) akan overflow untuk nilai > 127, sehingga digeser
        # -128 terlebih dahulu.
        quantized = (rgb.astype(np.int16) - 128).astype(np.int8)

        return np.expand_dims(quantized, axis=0)

    def save_image(
        self, image: np.ndarray, output_path: str | Path
    ) -> Path:
        """Menyimpan gambar ke disk, membuat folder tujuan jika perlu.

        Args:
            image: Gambar BGR yang akan disimpan.
            output_path: Path file tujuan (termasuk nama file).

        Returns:
            Path: Path file yang tersimpan.

        Raises:
            ValueError: Jika gambar kosong.
            IOError: Jika penulisan file gagal.
        """
        if image is None or image.size == 0:
            raise ValueError("Gambar kosong, tidak bisa disimpan.")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        success: bool = cv2.imwrite(str(path), image)
        if not success:
            raise IOError(f"Gagal menyimpan gambar ke: {path}")
        return path