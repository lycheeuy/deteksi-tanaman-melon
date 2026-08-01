"""Router monitoring server: CPU, RAM, disk, status layanan, uptime.

Terproteksi autentikasi karena mengekspos kondisi internal server.
Tidak mengubah Detection API, autentikasi, AI, maupun database.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import psutil
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.tflite_engine import TFLiteEngine
from app.config import settings
from app.db.session import get_db
from app.models import User
from app.services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Waktu proses backend mulai (modul ini diimpor saat startup).
_START_TIME: float = time.time()

_MB: int = 1024 * 1024
_GB: int = 1024 * 1024 * 1024


@router.get("/monitor")
def monitor(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Snapshot kondisi server untuk halaman System Status.

    Returns:
        dict: status layanan (backend/database/model), pemakaian
        CPU/RAM/disk, latency pemrosesan endpoint ini, uptime, dan
        waktu pembaruan terakhir.
    """
    start = time.perf_counter()

    # Status database: SELECT 1 — kegagalan tidak menggagalkan
    # endpoint, hanya dilaporkan "disconnected".
    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:  # noqa: BLE001
        database_status = "disconnected"

    model_loaded = TFLiteEngine().interpreter is not None

    cpu_percent: float = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    latency_ms: float = (time.perf_counter() - start) * 1000
    uptime_seconds: int = int(time.time() - _START_TIME)

    build_time: str = settings.BUILD_TIME or datetime.fromtimestamp(
        _START_TIME, tz=timezone.utc
    ).isoformat()
    model_name: str = (
        Path(settings.MODEL_PATH).name if settings.MODEL_PATH else "-"
    )

    response: dict[str, Any] = {
        "backend": "online",
        "app_version": settings.APP_VERSION,
        "build_time": build_time,
        "model_name": model_name,
        "environment": settings.APP_ENV,
        "database": database_status,
        "model": "loaded" if model_loaded else "not_loaded",
        "cpu": {"percent": round(cpu_percent, 1)},
        "memory": {
            "percent": round(memory.percent, 1),
            "used_mb": round(memory.used / _MB),
            "total_mb": round(memory.total / _MB),
        },
        "disk": {
            "percent": round(disk.percent, 1),
            "used_gb": round(disk.used / _GB, 1),
            "total_gb": round(disk.total / _GB, 1),
        },
        "latency_ms": round(latency_ms, 1),
        "uptime_seconds": uptime_seconds,
        "last_update": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "GET /monitor | user=%s | cpu=%.1f%% | ram=%.1f%% | disk=%.1f%% | "
        "db=%s | processing_time=%.3f sec",
        current_user.username,
        cpu_percent,
        memory.percent,
        disk.percent,
        database_status,
        time.perf_counter() - start,
    )
    return response