"""Router riwayat deteksi: list (search/filter/pagination) dan hapus.

Seluruh endpoint terproteksi autentikasi (Depends get_current_user)
karena menghapus data adalah operasi sensitif. API deteksi lama tidak
berubah.
"""

import logging
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.crud.detection_crud import (
    delete_detection,
    get_detection_by_id,
    search_detections,
)
from app.db.session import get_db
from app.models import DetectionResult, User
from app.schemas.detection import DetectionResponse
from app.services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Folder yang file-nya boleh ikut dihapus bersama record.
_DELETABLE_DIRS: frozenset[str] = frozenset({"uploads", "annotated"})


class BulkDeleteRequest(BaseModel):
    """Body DELETE /history untuk hapus banyak record sekaligus."""

    ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)


def _delete_record_files(record: DetectionResult) -> None:
    """Menghapus file gambar milik record (best-effort, hanya path
    relatif di dalam folder uploads/ atau annotated/)."""
    for relative in (record.image_path, record.annotated_image_path):
        if not relative:
            continue
        path = Path(relative)
        if path.is_absolute() or not path.parts:
            continue
        if path.parts[0] not in _DELETABLE_DIRS:
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Gagal menghapus file: %s", path)


@router.get("/history")
def list_history(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    search: str | None = Query(default=None, max_length=100),
    label: str | None = Query(default=None, max_length=50),
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Daftar riwayat deteksi dengan search, filter, dan pagination.

    Returns:
        dict: items, total, page, page_size, total_pages.
    """
    start = time.perf_counter()
    offset = (page - 1) * page_size
    items, total = search_detections(
        db,
        search=search,
        label=label,
        date_from=date_from,
        date_to=date_to,
        limit=page_size,
        offset=offset,
    )
    total_pages = max(1, -(-total // page_size))  # ceil division

    logger.info(
        "GET /history | user=%s | page=%d | total=%d | "
        "processing_time=%.3f sec",
        current_user.username,
        page,
        total,
        time.perf_counter() - start,
    )
    return {
        "items": [
            DetectionResponse.model_validate(item).model_dump()
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.delete("/history/{record_id}")
def delete_history(
    request: Request,
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Menghapus satu record riwayat beserta file gambarnya.

    Raises:
        HTTPException: 404 bila record tidak ditemukan.
    """
    record = get_detection_by_id(db, record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record tidak ditemukan.",
        )

    _delete_record_files(record)
    delete_detection(db, record_id)

    logger.info(
        "DELETE /history | user=%s | record_id=%s | timestamp=%s",
        current_user.username,
        record_id,
        datetime.now(timezone.utc).isoformat(),
    )
    return {"deleted": True, "id": str(record_id)}


@router.delete("/history")
def bulk_delete_history(
    request: Request,
    body: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Menghapus banyak record riwayat sekaligus (maks. 100).

    Returns:
        dict: deleted (jumlah terhapus), not_found (jumlah tidak
        ditemukan).
    """
    deleted = 0
    not_found = 0
    for record_id in body.ids:
        record = get_detection_by_id(db, record_id)
        if record is None:
            not_found += 1
            continue
        _delete_record_files(record)
        delete_detection(db, record_id)
        deleted += 1
        logger.info(
            "DELETE /history (bulk) | user=%s | record_id=%s | "
            "timestamp=%s",
            current_user.username,
            record_id,
            datetime.now(timezone.utc).isoformat(),
        )

    logger.info(
        "DELETE /history (bulk) | user=%s | deleted=%d | not_found=%d",
        current_user.username,
        deleted,
        not_found,
    )
    return {"deleted": deleted, "not_found": not_found}