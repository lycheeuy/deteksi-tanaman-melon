"""Router REST API untuk prediksi Deteksi Tanaman Melon.

Endpoint:
    GET  /         : Informasi API.
    GET  /health   : Health check.
    POST /predict  : Inferensi mentah dari gambar upload.
"""

import logging
import shutil
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.services.prediction_service import PredictionService

logger = logging.getLogger(__name__)

router = APIRouter()

TEMP_DIR = Path("uploads/temp")
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})
ALLOWED_MIME_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png"})


@lru_cache
def get_prediction_service() -> PredictionService:
    """Dependency penyedia PredictionService (dibuat satu kali).

    Returns:
        PredictionService: Instance siap-pakai dengan model termuat.

    Raises:
        HTTPException: 503 jika model gagal dimuat.
    """
    try:
        return PredictionService()
    except (FileNotFoundError, RuntimeError) as exc:
        logger.error("PredictionService gagal diinisialisasi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model AI tidak tersedia. Hubungi administrator.",
        ) from exc


@router.get("/")
def read_root() -> dict[str, str]:
    """Informasi dasar API."""
    return {
        "message": "Deteksi Tanaman Melon API",
        "status": "running",
    }


@router.post("/predict")
async def predict(
    image: UploadFile,
    service: PredictionService = Depends(get_prediction_service),
) -> dict[str, Any]:
    """Menjalankan inferensi mentah terhadap gambar yang di-upload.

    Alur: validasi ekstensi + MIME type -> simpan sementara ke
    uploads/temp/ -> inferensi via PredictionService (dengan logging
    waktu inferensi) -> hapus file temporary.

    Args:
        image: File gambar (multipart/form-data, field "image").
        service: PredictionService dari dependency injection.

    Returns:
        dict: success, input_shape, output_shape, raw_output_shape
        (tanpa tensor mentah).

    Raises:
        HTTPException: 400 jika ekstensi/MIME type tidak didukung atau
            file bukan gambar valid, 500 jika inferensi gagal.
    """
    # 1a. Validasi ekstensi file.
    extension = Path(image.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Ekstensi '{extension}' tidak didukung. "
                f"Gunakan: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )

    # 1b. Validasi MIME type dari header upload.
    if image.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="File harus berupa JPG atau PNG.",
        )

    temp_path: Path | None = None
    try:
        # 2. Simpan sementara dengan nama unik agar request paralel aman.
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        temp_path = TEMP_DIR / f"{uuid.uuid4().hex}{extension}"
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        logger.info("File temporary tersimpan: %s", temp_path)

        # 3. Inferensi dengan pengukuran waktu.
        start = time.perf_counter()
        result = service.predict_image(temp_path)
        elapsed = time.perf_counter() - start
        logger.info("Inference time: %.3f sec", elapsed)

        return {
            "success": True,
            "input_shape": list(result["input_shape"]),
            "output_shape": [list(s) for s in result["output_shape"]],
            "raw_output_shape": [
                list(out.shape) for out in result["raw_output"]
            ],
        }
    except ValueError as exc:
        logger.warning("File upload bukan gambar valid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File tidak dapat dibaca sebagai gambar.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Inferensi gagal: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan saat menjalankan inferensi.",
        ) from exc
    finally:
        # 4. Hapus file temporary apa pun hasilnya.
        if temp_path and temp_path.exists():
            temp_path.unlink()
            logger.info("File temporary dihapus: %s", temp_path)