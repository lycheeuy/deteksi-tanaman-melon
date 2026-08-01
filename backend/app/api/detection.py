"""Router REST API final: pipeline deteksi lengkap Deteksi Tanaman Melon.

Endpoint:
    POST /detect : upload -> DetectionService -> AnnotationService ->
                   HistoryService -> JSON response.
"""

import logging
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.services.annotation_service import AnnotationService
from app.services.detection_service import DetectionService
from app.services.history_service import HistoryService

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})


@lru_cache
def get_detection_service() -> DetectionService:
    """Dependency DetectionService (dibuat satu kali).

    Raises:
        HTTPException: 503 jika model gagal dimuat.
    """
    try:
        return DetectionService()
    except (FileNotFoundError, RuntimeError) as exc:
        logger.error("DetectionService gagal diinisialisasi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model AI tidak tersedia. Hubungi administrator.",
        ) from exc


@lru_cache
def get_annotation_service() -> AnnotationService:
    """Dependency AnnotationService (dibuat satu kali)."""
    return AnnotationService()


def get_history_service(
    detection_service: DetectionService = Depends(get_detection_service),
) -> HistoryService:
    """Dependency HistoryService yang berbagi DetectionService yang sama,
    sehingga model tetap hanya dimuat satu kali."""
    return HistoryService(detection_service=detection_service)


@router.post("/detect")
async def detect(
    image: UploadFile,
    detection_service: DetectionService = Depends(get_detection_service),
    annotation_service: AnnotationService = Depends(get_annotation_service),
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    """Pipeline lengkap: upload -> deteksi -> anotasi -> history -> JSON.

    Args:
        image: File gambar (multipart/form-data, field "image").
        detection_service: Pipeline AI.
        annotation_service: Penggambar hasil deteksi.
        history_service: Penyimpan riwayat ke database.

    Returns:
        dict: success, message, record_id, image_path,
        annotated_image_path, total_detection, detections.

    Raises:
        HTTPException: 400 gambar kosong/tidak valid, 404 file tidak
            ditemukan saat diproses, 500 kesalahan internal.
    """
    start = time.perf_counter()
    logger.info("Upload diterima | filename=%s", image.filename)

    # Validasi dasar upload.
    extension = Path(image.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Ekstensi '{extension}' tidak didukung. "
                f"Gunakan: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )

    contents: bytes = await image.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gambar kosong.",
        )

    # 1. Simpan upload permanen dengan nama unik (dirujuk oleh history).
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"

    try:
        upload_path.write_bytes(contents)

        # 2. Deteksi (inferensi hanya SATU KALI di sini).
        detection_result = detection_service.detect_image(upload_path)

        # 3. Anotasi.
        annotated_path_str: str = annotation_service.annotate_image(
            str(upload_path), detection_result["detections"]
        )

        # Relative path bergaya posix (forward slash) untuk response
        # dan database, agar konsisten lintas OS dan siap dipakai
        # frontend.
        image_path_rel: str = upload_path.as_posix()
        annotated_path_rel: str = Path(annotated_path_str).as_posix()

        # 4. Simpan riwayat: murni persistensi, tanpa inferensi ulang.
        saved = history_service.save_detection_result(
            image_path=image_path_rel,
            detection_result=detection_result,
            annotated_image_path=annotated_path_rel,
        )

        elapsed = time.perf_counter() - start
        logger.info(
            "Pipeline selesai | filename=%s | total_detection=%d | "
            "processing_time=%.3f sec",
            image.filename,
            detection_result["total_detection"],
            elapsed,
        )

        # 5. Response JSON (relative path, bukan absolute).
        return {
            "success": True,
            "message": "Detection completed",
            "record_id": saved["record_id"],
            "image_path": image_path_rel,
            "annotated_image_path": annotated_path_rel,
            "total_detection": detection_result["total_detection"],
            "detections": detection_result["detections"],
        }
    except HTTPException:
        upload_path.unlink(missing_ok=True)
        raise
    except FileNotFoundError as exc:
        upload_path.unlink(missing_ok=True)
        logger.warning("File tidak ditemukan saat diproses: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File tidak ditemukan saat diproses.",
        ) from exc
    except ValueError as exc:
        upload_path.unlink(missing_ok=True)
        logger.warning("Upload bukan gambar valid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File tidak dapat dibaca sebagai gambar.",
        ) from exc
    except Exception as exc:
        upload_path.unlink(missing_ok=True)
        logger.error("Pipeline gagal: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal saat memproses gambar.",
        ) from exc