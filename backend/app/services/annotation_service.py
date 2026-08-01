"""Annotation Service: menggambar hasil deteksi pada gambar (OpenCV).

Menggambar rectangle hijau per grid cell terdeteksi beserta label dan
confidence. Tidak menjalankan inferensi dan tidak menyentuh database
(SRP) — murni menerima daftar deteksi lalu menghasilkan file anotasi.
"""

import logging
from pathlib import Path

import cv2
import numpy as np

from app.services.image_service import ImageService

logger = logging.getLogger(__name__)

ANNOTATED_DIR = Path("annotated")

# Gaya anotasi.
BOX_COLOR: tuple[int, int, int] = (0, 255, 0)  # Hijau (BGR)
BOX_THICKNESS: int = 2
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE: float = 0.5
FONT_THICKNESS: int = 1
TEXT_COLOR: tuple[int, int, int] = (0, 255, 0)
LINE_SPACING: int = 18


class AnnotationService:
    """Layanan anotasi gambar hasil deteksi FOMO."""

    def __init__(self, grid_width: int = 12, grid_height: int = 12) -> None:
        """Menginisialisasi AnnotationService.

        Args:
            grid_width: Jumlah kolom grid output model FOMO. Default 12
                sesuai output shape model saat ini (1, 12, 12, C) —
                dapat diubah tanpa menyentuh kode jika model berganti.
            grid_height: Jumlah baris grid output model FOMO.

        Raises:
            ValueError: Jika ukuran grid tidak positif.
        """
        if grid_width <= 0 or grid_height <= 0:
            raise ValueError(
                f"Ukuran grid harus positif, diterima: "
                f"{grid_width}x{grid_height}"
            )
        self.grid_width: int = grid_width
        self.grid_height: int = grid_height
        self.image_service: ImageService = ImageService()

    @staticmethod
    def _build_output_path(image_path: str | Path) -> Path:
        """Menyusun path output: annotated/<nama>_annotated.jpg."""
        stem = Path(image_path).stem
        return ANNOTATED_DIR / f"{stem}_annotated.jpg"

    def _draw_detection(
        self,
        image: np.ndarray,
        detection: dict,
        cell_width: float,
        cell_height: float,
    ) -> None:
        """Menggambar satu deteksi: rectangle + label + confidence.

        Args:
            image: Gambar BGR yang digambar in-place.
            detection: Dict deteksi (label, confidence, grid_x, grid_y).
            cell_width: Lebar satu grid cell dalam piksel.
            cell_height: Tinggi satu grid cell dalam piksel.
        """
        height, width = image.shape[:2]

        # Rectangle mengelilingi grid cell (tanpa hardcode ukuran).
        x1 = int(detection["grid_x"] * cell_width)
        y1 = int(detection["grid_y"] * cell_height)
        x2 = int(min((detection["grid_x"] + 1) * cell_width, width - 1))
        y2 = int(min((detection["grid_y"] + 1) * cell_height, height - 1))
        cv2.rectangle(image, (x1, y1), (x2, y2), BOX_COLOR, BOX_THICKNESS)

        # Dua baris teks: nama kelas lalu confidence (mis. 98.23%).
        label_text: str = str(detection.get("label", "Unknown"))
        confidence_text: str = f"{detection['confidence'] * 100:.2f}%"

        # Posisi teks di atas kotak; jika mepet tepi atas, taruh di
        # dalam kotak agar tidak terpotong.
        text_y = y1 - LINE_SPACING - 4
        if text_y < LINE_SPACING:
            text_y = y1 + LINE_SPACING

        for line in (label_text, confidence_text):
            cv2.putText(
                image,
                line,
                (x1, text_y),
                FONT,
                FONT_SCALE,
                TEXT_COLOR,
                FONT_THICKNESS,
                cv2.LINE_AA,
            )
            text_y += LINE_SPACING

    def annotate_image(
        self, image_path: str, detections: list
    ) -> str:
        """Menggambar seluruh deteksi lalu menyimpan gambar anotasi.

        Jika daftar deteksi kosong, gambar tetap disimpan tanpa
        rectangle.

        Args:
            image_path: Path gambar sumber.
            detections: Daftar deteksi dari DetectionService, tiap
                elemen memuat label, confidence, grid_x, grid_y.

        Returns:
            str: Path file gambar hasil anotasi
                (annotated/<nama>_annotated.jpg).

        Raises:
            FileNotFoundError: Jika gambar sumber tidak ditemukan.
            ValueError: Jika file bukan gambar valid.
            IOError: Jika penyimpanan hasil gagal.
        """
        image: np.ndarray = self.image_service.load_image(image_path)
        height, width = image.shape[:2]

        # Ukuran cell dihitung dari dimensi gambar aktual.
        cell_width: float = width / self.grid_width
        cell_height: float = height / self.grid_height

        for detection in detections:
            self._draw_detection(image, detection, cell_width, cell_height)

        output_path: Path = self._build_output_path(image_path)
        saved_path: Path = self.image_service.save_image(image, output_path)

        logger.info(
            "Anotasi selesai | jumlah objek=%d | output=%s",
            len(detections),
            saved_path,
        )
        return str(saved_path)