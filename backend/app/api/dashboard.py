"""Router API statistik dashboard frontend."""

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.ai.tflite_engine import TFLiteEngine
from app.crud.detection_crud import (
    count_detections,
    count_detections_by_label,
    count_detections_today,
    count_no_detection,
    get_all_detections,
)
from app.db.session import get_db
from app.schemas.detection import DetectionResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard/summary")
def dashboard_summary(
    request: Request, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Ringkasan statistik untuk kartu dashboard frontend.

    Returns:
        dict: total_detection, today_detection, database, model,
        backend. Jika database tidak dapat diakses, request gagal
        (500) dan frontend menampilkan error state.
    """
    start = time.perf_counter()

    total: int = count_detections(db)
    today: int = count_detections_today(db)
    no_detection: int = count_no_detection(db)
    label_counts = count_detections_by_label(db)
    model_loaded: bool = TFLiteEngine().interpreter is not None

    response: dict[str, Any] = {
        "total_detection": total,
        "today_detection": today,
        "no_detection": no_detection,
        "labels": [
            {"label": label, "count": count}
            for label, count in label_counts
            if label != "No Detection"
        ],
        "database": "connected",
        "model": "loaded" if model_loaded else "not_loaded",
        "backend": "online",
    }
    logger.info(
        "GET /dashboard/summary | client_ip=%s | processing_time=%.3f sec | "
        "total=%d | today=%d",
        request.client.host if request.client else "-",
        time.perf_counter() - start,
        total,
        today,
    )
    return response


@router.get("/dashboard/recent")
def dashboard_recent(
    request: Request, limit: int = 5, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Daftar deteksi terbaru untuk panel Recent History dashboard.

    Args:
        limit: Jumlah record (1-20, default 5).

    Returns:
        dict: {"items": [record terbaru, terurut detected_at menurun]}.
    """
    start = time.perf_counter()
    safe_limit: int = max(1, min(limit, 20))
    records = get_all_detections(db, limit=safe_limit, offset=0)
    items = [
        DetectionResponse.model_validate(record).model_dump()
        for record in records
    ]
    logger.info(
        "GET /dashboard/recent | client_ip=%s | processing_time=%.3f sec | "
        "items=%d",
        request.client.host if request.client else "-",
        time.perf_counter() - start,
        len(items),
    )
    return {"items": items}