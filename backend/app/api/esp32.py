"""Router API untuk integrasi ESP32-CAM dan monitoring sistem.

Endpoint:
    POST /api/esp32/detect : pipeline lengkap, response ringkas untuk
                             firmware ESP32.
    GET  /health           : health check database + model.
    GET  /system/info      : informasi versi dan konfigurasi sistem.
"""

import logging
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import tensorflow as tf
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy import text

from app.ai.labels import LABELS
from app.ai.tflite_engine import TFLiteEngine
from app.api.detection import (
    ALLOWED_EXTENSIONS,
    UPLOAD_DIR,
    get_annotation_service,
    get_detection_service,
    get_history_service,
)
from app.config import settings
from app.db.session import SessionLocal
from app.services.annotation_service import AnnotationService
from app.services.detection_service import DetectionService
from app.services.history_service import HistoryService

logger = logging.getLogger(__name__)

router = APIRouter()

APP_VERSION: str = "1.0.0"

# Validasi upload ESP32 — selaras dengan batas di halaman Detect.
ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png"}
)
MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------
# Antrean perintah (command queue) untuk tombol Detect di dashboard.
#
# Backend tidak dapat menghubungi ESP32 yang berada di balik NAT, maka
# arah koneksi dibalik: dashboard MENITIPKAN perintah di sini, dan
# ESP32 MENJEMPUTNYA lewat polling GET /api/esp32/command.
# Perintah bersifat sekali-pakai dan kedaluwarsa otomatis agar
# perangkat yang baru online tidak menjalankan perintah basi.
# ---------------------------------------------------------------------

DEFAULT_DEVICE_ID: str = "esp32-cam"
COMMAND_TTL_SECONDS: float = 60.0

# device_id -> timestamp saat perintah dititipkan.
_pending_commands: dict[str, float] = {}
_command_lock = threading.Lock()


def _check_database() -> bool:
    """Menguji koneksi database dengan query ringan.

    Returns:
        bool: True jika SELECT 1 berhasil.
    """
    try:
        session = SessionLocal()
        try:
            session.execute(text("SELECT 1"))
            return True
        finally:
            session.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check database gagal: %s", exc)
        return False


def _model_loaded() -> bool:
    """Memeriksa apakah model TFLite sudah termuat (tanpa memaksa load)."""
    return TFLiteEngine().interpreter is not None


@router.get("/health")
def health_check(request: Request) -> dict[str, str]:
    """Health check sistem: status database dan model.

    Returns:
        dict: status, database, model, version.
    """
    start = time.perf_counter()
    database_ok = _check_database()
    model_ok = _model_loaded()

    response = {
        "status": "ok" if (database_ok and model_ok) else "degraded",
        "database": "connected" if database_ok else "disconnected",
        "model": "loaded" if model_ok else "not_loaded",
        "version": APP_VERSION,
    }
    logger.info(
        "GET /health | client_ip=%s | processing_time=%.3f sec | status=%s",
        request.client.host if request.client else "-",
        time.perf_counter() - start,
        response["status"],
    )
    return response


@router.get("/system/info")
def system_info(request: Request) -> dict[str, Any]:
    """Informasi sistem: versi aplikasi, TensorFlow, dan model.

    Returns:
        dict: app_version, tensorflow_version, model_input_size,
        total_labels, model_path.
    """
    start = time.perf_counter()

    # Ukuran input model hanya tersedia jika model sudah termuat.
    engine = TFLiteEngine()
    if engine.interpreter is not None and engine.input_details:
        model_input_size: Any = [
            int(dim) for dim in engine.input_details[0]["shape"]
        ]
    else:
        model_input_size = "unknown (model belum dimuat)"

    response: dict[str, Any] = {
        "app_version": APP_VERSION,
        "tensorflow_version": tf.__version__,
        "model_input_size": model_input_size,
        "total_labels": len(LABELS),
        "model_path": settings.MODEL_PATH,
    }
    logger.info(
        "GET /system/info | client_ip=%s | processing_time=%.3f sec",
        request.client.host if request.client else "-",
        time.perf_counter() - start,
    )
    return response


@router.post("/api/esp32/detect")
async def esp32_detect(
    request: Request,
    image: UploadFile,
    detection_service: DetectionService = Depends(get_detection_service),
    annotation_service: AnnotationService = Depends(get_annotation_service),
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    """Pipeline deteksi lengkap dengan response ringkas untuk ESP32.

    Alur sama dengan POST /detect (upload -> deteksi -> anotasi ->
    history), tetapi JSON response dipangkas agar mudah di-parse oleh
    firmware dengan memori terbatas.

    Args:
        request: Request FastAPI (untuk client IP).
        image: File gambar (multipart/form-data, field "image").

    Returns:
        dict: success, label, total_detection — ditambah record_id dan
        annotated_image bila ada deteksi.

    Raises:
        HTTPException: 400 gambar kosong/tidak valid, 404 file hilang
            saat diproses, 500 kesalahan internal.
    """
    start = time.perf_counter()
    client_ip: str = request.client.host if request.client else "-"

    # Identitas request untuk debugging lintas log <-> response.
    request_id: str = uuid.uuid4().hex[:12]
    # Identitas perangkat: header opsional X-Device-Id (maks 64 char),
    # default "esp32-cam" bila firmware tidak mengirimkannya.
    device: str = (
        request.headers.get("X-Device-Id", "esp32-cam") or "esp32-cam"
    )[:64]

    extension = Path(image.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Ekstensi '{extension}' tidak didukung. "
                f"Gunakan: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )

    content_type: str = (image.content_type or "").lower()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Content-Type '{content_type or '-'}' tidak didukung. "
                "Gunakan image/jpeg atau image/png."
            ),
        )

    contents: bytes = await image.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gambar kosong.",
        )
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,  # Content Too Large
            detail=(
                f"Ukuran gambar {len(contents) / (1024 * 1024):.1f} MB "
                "melebihi batas 10 MB."
            ),
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"

    try:
        upload_path.write_bytes(contents)

        detection_result = detection_service.detect_image(upload_path)

        annotated_path_str: str = annotation_service.annotate_image(
            str(upload_path), detection_result["detections"]
        )
        image_path_rel: str = upload_path.as_posix()
        annotated_path_rel: str = Path(annotated_path_str).as_posix()

        saved = history_service.save_detection_result(
            image_path=image_path_rel,
            detection_result=detection_result,
            annotated_image_path=annotated_path_rel,
        )

        total: int = detection_result["total_detection"]
        elapsed = time.perf_counter() - start
        logger.info(
            "POST /api/esp32/detect | request_id=%s | device=%s | "
            "client_ip=%s | processing_time=%.3f sec | "
            "total_detection=%d",
            request_id,
            device,
            client_ip,
            elapsed,
            total,
        )

        # Response KONSISTEN: 5 field yang sama pada semua kondisi,
        # agar parser firmware ESP32 sederhana dan deterministik.
        top_label: str = (
            detection_result["detections"][0]["label"]
            if total > 0
            else "No Detection"
        )
        return {
            "success": True,
            "label": top_label,
            "total_detection": total,
            "record_id": saved["record_id"],
            "annotated_image": annotated_path_rel,
            "device": device,
            "request_id": request_id,
        }
    except HTTPException:
        upload_path.unlink(missing_ok=True)
        raise
    except FileNotFoundError as exc:
        upload_path.unlink(missing_ok=True)
        logger.warning(
            "File tidak ditemukan saat diproses | request_id=%s | %s",
            request_id, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File tidak ditemukan saat diproses.",
        ) from exc
    except ValueError as exc:
        upload_path.unlink(missing_ok=True)
        logger.warning(
            "Upload bukan gambar valid | request_id=%s | %s",
            request_id, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File tidak dapat dibaca sebagai gambar.",
        ) from exc
    except Exception as exc:
        upload_path.unlink(missing_ok=True)
        logger.error(
            "Pipeline ESP32 gagal | request_id=%s | %s",
            request_id, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal saat memproses gambar.",
        ) from exc


def _esp32_get(path: str, timeout: float) -> bytes:
    """Mengambil resource dari ESP32-CAM (server-side, bebas CORS).

    Args:
        path: Path pada ESP32, mis. "/capture".
        timeout: Batas waktu koneksi dalam detik.

    Returns:
        bytes: Isi response.

    Raises:
        RuntimeError: Jika ESP32_URL belum diatur.
        Exception: Diteruskan bila ESP32 tidak dapat dihubungi.
    """
    if not settings.ESP32_URL:
        raise RuntimeError("ESP32_URL belum diatur di .env backend.")
    with urllib.request.urlopen(
        f"{settings.ESP32_URL}{path}", timeout=timeout
    ) as response:
        return response.read()


@router.get("/api/esp32/status")
def esp32_status(request: Request) -> dict[str, Any]:
    """Memeriksa apakah ESP32-CAM dapat dihubungi dari backend.

    Returns:
        dict: esp32 ("online" / "offline" / "unconfigured") dan
        esp32_url.
    """
    start = time.perf_counter()
    if not settings.ESP32_URL:
        return {"esp32": "unconfigured", "esp32_url": None}

    online: bool = False
    # Firmware CameraWebServer menyediakan /status; jika tidak ada,
    # jatuh ke root sebagai cadangan.
    for probe in ("/status", "/"):
        try:
            _esp32_get(probe, timeout=3.0)
            online = True
            break
        except Exception:  # noqa: BLE001
            continue

    logger.info(
        "GET /api/esp32/status | client_ip=%s | processing_time=%.3f sec | "
        "esp32=%s",
        request.client.host if request.client else "-",
        time.perf_counter() - start,
        "online" if online else "offline",
    )
    return {
        "esp32": "online" if online else "offline",
        "esp32_url": settings.ESP32_URL,
    }


@router.post("/api/esp32/capture-detect")
async def esp32_capture_detect(
    request: Request,
    detection_service: DetectionService = Depends(get_detection_service),
    annotation_service: AnnotationService = Depends(get_annotation_service),
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    """Mengambil snapshot dari ESP32-CAM lalu menjalankan pipeline
    deteksi lengkap (deteksi -> anotasi -> history).

    Snapshot diambil oleh BACKEND dari {ESP32_URL}/capture sehingga
    bebas dari masalah CORS browser. DetectionService tidak diubah.

    Returns:
        dict: Response lengkap seperti POST /detect (success, message,
        record_id, image_path, annotated_image_path, total_detection,
        detections).

    Raises:
        HTTPException: 503 bila ESP32_URL belum diatur, 502 bila ESP32
            tidak dapat dihubungi, 500 untuk kegagalan pipeline.
    """
    start = time.perf_counter()
    client_ip: str = request.client.host if request.client else "-"

    if not settings.ESP32_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32_URL belum diatur di .env backend.",
        )

    try:
        image_bytes: bytes = _esp32_get("/capture", timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Snapshot ESP32 gagal: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ESP32 tidak dapat dihubungi.",
        ) from exc

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ESP32 mengirim snapshot kosong.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = UPLOAD_DIR / f"{uuid.uuid4().hex}.jpg"

    try:
        upload_path.write_bytes(image_bytes)

        detection_result = detection_service.detect_image(upload_path)
        annotated_path_str: str = annotation_service.annotate_image(
            str(upload_path), detection_result["detections"]
        )
        image_path_rel: str = upload_path.as_posix()
        annotated_path_rel: str = Path(annotated_path_str).as_posix()

        saved = history_service.save_detection_result(
            image_path=image_path_rel,
            detection_result=detection_result,
            annotated_image_path=annotated_path_rel,
        )

        elapsed = time.perf_counter() - start
        logger.info(
            "POST /api/esp32/capture-detect | client_ip=%s | "
            "processing_time=%.3f sec | total_detection=%d",
            client_ip,
            elapsed,
            detection_result["total_detection"],
        )

        return {
            "success": True,
            "message": "Detection completed",
            "record_id": saved["record_id"],
            "image_path": image_path_rel,
            "annotated_image_path": annotated_path_rel,
            "total_detection": detection_result["total_detection"],
            "detections": detection_result["detections"],
        }
    except ValueError as exc:
        upload_path.unlink(missing_ok=True)
        logger.warning("Snapshot bukan gambar valid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Snapshot ESP32 bukan gambar valid.",
        ) from exc
    except HTTPException:
        upload_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        upload_path.unlink(missing_ok=True)
        logger.error("Pipeline capture-detect gagal: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal saat memproses snapshot.",
        ) from exc


@router.post("/api/esp32/command/detect")
def queue_detect_command(
    request: Request, device: str = DEFAULT_DEVICE_ID
) -> dict[str, Any]:
    """Menitipkan perintah deteksi untuk perangkat (dipanggil dashboard).

    Perintah disimpan sampai dijemput ESP32 lewat GET
    /api/esp32/command, atau kedaluwarsa setelah COMMAND_TTL_SECONDS.

    Args:
        device: Identitas perangkat tujuan (default "esp32-cam").

    Returns:
        dict: {"queued": True, "device": ..., "ttl_seconds": ...}
    """
    with _command_lock:
        _pending_commands[device] = time.time()

    logger.info(
        "POST /api/esp32/command/detect | device=%s | client_ip=%s",
        device,
        request.client.host if request.client else "-",
    )
    return {
        "queued": True,
        "device": device,
        "ttl_seconds": COMMAND_TTL_SECONDS,
    }


@router.get("/api/esp32/command")
def poll_command(request: Request) -> dict[str, Any]:
    """Dijemput ESP32 secara berkala: adakah perintah tertunda?

    Identitas perangkat dibaca dari header X-Device-Id (default
    "esp32-cam"). Perintah bersifat sekali-pakai: setelah dijemput,
    antrean langsung dikosongkan.

    Returns:
        dict: {"detect": bool} — True bila ada perintah yang masih
        berlaku.
    """
    device: str = (
        request.headers.get("X-Device-Id", DEFAULT_DEVICE_ID)
        or DEFAULT_DEVICE_ID
    )[:64]

    with _command_lock:
        queued_at = _pending_commands.pop(device, None)

    if queued_at is None:
        return {"detect": False}

    age: float = time.time() - queued_at
    if age > COMMAND_TTL_SECONDS:
        logger.info(
            "Perintah basi diabaikan | device=%s | umur=%.1f dtk",
            device,
            age,
        )
        return {"detect": False}

    logger.info(
        "Perintah detect dijemput | device=%s | umur=%.1f dtk", device, age
    )
    return {"detect": True}