"""History Service: menyimpan hasil deteksi sebagai riwayat di database.

Menghubungkan DetectionService (pipeline AI) dengan CRUD
DetectionResult. Seluruh akses database dilakukan melalui layer CRUD —
tidak ada query SQLAlchemy langsung di service ini (SRP).
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.crud.detection_crud import create_detection, get_detection_by_id
from app.db.session import SessionLocal
from app.schemas.detection import DetectionCreate, DetectionResponse
from app.services.detection_service import DetectionService

logger = logging.getLogger(__name__)

NO_DETECTION_LABEL: str = "No Detection"
NO_DETECTION_ACTION: str = "None"

# Placeholder sampai rule engine rekomendasi dibuat pada fase berikutnya.
DEFAULT_ACTION: str = "None"


class HistoryService:
    """Service riwayat: menyimpan hasil deteksi ke database."""

    def __init__(
        self, detection_service: DetectionService | None = None
    ) -> None:
        """Menginisialisasi HistoryService.

        Args:
            detection_service: Instance DetectionService. Jika None,
                dibuat baru (parameter ini memudahkan dependency
                injection saat pengujian).

        Raises:
            FileNotFoundError: Jika file model tidak ditemukan.
            RuntimeError: Jika model gagal dimuat.
        """
        self.detection_service: DetectionService = (
            detection_service or DetectionService()
        )
        logger.info("HistoryService siap digunakan.")

    def save_detection_result(
        self,
        image_path: str,
        detection_result: dict,
        annotated_image_path: str | None = None,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Menyimpan hasil deteksi YANG SUDAH ADA ke database.

        Tidak menjalankan inferensi — murni persistensi, sehingga
        pemanggil (mis. endpoint /detect) cukup melakukan inferensi
        satu kali lalu menyerahkan hasilnya ke sini.

        Args:
            image_path: Path gambar sumber.
            detection_result: Hasil DetectionService.detect_image(),
                memuat "total_detection" dan "detections" (terurut
                confidence menurun).
            annotated_image_path: Path gambar anotasi (opsional),
                disimpan ke kolom annotated_image_path.
            db: Session database opsional. Jika None, session dibuat
                dan ditutup secara internal.

        Returns:
            dict: {
                "saved": True,
                "record_id": str UUID record,
                "result": dict record tersimpan (DetectionResponse),
                "confidence": float | None — hanya in-memory untuk
                    logging/pengujian, tidak pernah disimpan ke
                    database maupun diekspos ke API.
            }

        Raises:
            KeyError: Jika detection_result tidak memuat field wajib.
        """
        # Tentukan label dan confidence dari hasil deteksi.
        if detection_result["total_detection"] == 0:
            label: str = NO_DETECTION_LABEL
            action: str = NO_DETECTION_ACTION
            confidence: float | None = None
        else:
            # Deteksi terbaik = elemen pertama (sudah terurut menurun).
            best: dict[str, Any] = detection_result["detections"][0]
            label = best["label"]
            action = DEFAULT_ACTION
            confidence = float(best["confidence"])

        payload = DetectionCreate(
            image_path=str(image_path),
            annotated_image_path=annotated_image_path,
            label=label,
            action=action,
        )

        # Kelola session: pakai yang diberikan, atau buka-tutup sendiri.
        own_session: bool = db is None
        session: Session = db if db is not None else SessionLocal()
        try:
            record = create_detection(session, payload)
            record_id: str = str(record.id)
            result: dict[str, Any] = DetectionResponse.model_validate(
                record
            ).model_dump()
        finally:
            if own_session:
                session.close()

        logger.info(
            "Riwayat tersimpan | image_path=%s | label=%s | "
            "confidence=%s | record_id=%s",
            image_path,
            label,
            f"{confidence:.4f}" if confidence is not None else "-",
            record_id,
        )

        return {
            "saved": True,
            "record_id": record_id,
            "result": result,
            "confidence": confidence,
        }

    def save_detection(
        self, image_path: str, db: Session | None = None
    ) -> dict[str, Any]:
        """Mendeteksi gambar lalu menyimpan hasilnya (inferensi 1x).

        Alur: DetectionService.detect_image() ->
        save_detection_result(). Cocok untuk pemakaian mandiri; untuk
        endpoint yang sudah punya hasil deteksi, panggil langsung
        save_detection_result() agar inferensi tidak berulang.

        Args:
            image_path: Path menuju file gambar.
            db: Session database opsional.

        Returns:
            dict: Sama seperti save_detection_result().

        Raises:
            FileNotFoundError: Jika file gambar tidak ditemukan.
            ValueError: Jika file bukan gambar valid.
            RuntimeError: Jika inferensi gagal.
        """
        detection_result = self.detection_service.detect_image(image_path)
        return self.save_detection_result(
            image_path=image_path,
            detection_result=detection_result,
            db=db,
        )

    def get_history_by_id(
        self, record_id: Any, db: Session | None = None
    ) -> dict[str, Any] | None:
        """Mengambil kembali satu record riwayat via CRUD (verifikasi).

        Args:
            record_id: UUID record yang dicari.
            db: Session database opsional.

        Returns:
            dict | None: Record dalam bentuk dict, atau None jika
            tidak ditemukan.
        """
        own_session: bool = db is None
        session: Session = db if db is not None else SessionLocal()
        try:
            record = get_detection_by_id(session, record_id)
            if record is None:
                return None
            return DetectionResponse.model_validate(record).model_dump()
        finally:
            if own_session:
                session.close()