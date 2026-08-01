"""Router ekspor laporan riwayat deteksi (CSV & Excel).

Data dialirkan sebagai StreamingResponse langsung dari database —
tidak ada file permanen yang dibuat di server. Kedua endpoint
terproteksi autentikasi karena berisi data riwayat.
"""

import csv
import io
import logging
import time
from collections.abc import Iterator
from datetime import date, datetime


from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.crud.detection_crud import search_detections
from app.db.session import get_db
from app.models import DetectionResult, User
from app.services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Kolom laporan — urutan tetap untuk CSV maupun Excel.
_COLUMNS: tuple[str, ...] = (
    "id",
    "label",
    "action",
    "image_path",
    "annotated_image_path",
    "detected_at",
)

# Ukuran halaman pengambilan data per batch (hemat memori).
_PAGE_SIZE: int = 500


def _iter_records(
    db: Session,
    label: str | None,
    date_from: date | None,
    date_to: date | None,
) -> Iterator[DetectionResult]:
    """Mengalirkan seluruh record yang cocok filter, per batch 500."""
    offset = 0
    while True:
        items, total = search_detections(
            db,
            label=label,
            date_from=date_from,
            date_to=date_to,
            limit=_PAGE_SIZE,
            offset=offset,
        )
        yield from items
        offset += _PAGE_SIZE
        if not items or offset >= total:
            break


def _record_row(record: DetectionResult) -> list[str]:
    """Mengubah satu record menjadi satu baris laporan."""
    return [
        str(record.id),
        record.label,
        record.action,
        record.image_path,
        record.annotated_image_path or "",
        record.detected_at.isoformat(),
    ]


def _export_filename(extension: str) -> str:
    """Nama file unduhan berstempel waktu."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"laporan_deteksi_melon_{stamp}.{extension}"


@router.get("/report/export/csv")
def export_csv(
    request: Request,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    label: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Mengekspor riwayat deteksi sebagai CSV (streaming, tanpa file
    permanen)."""
    start = time.perf_counter()

    def stream() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        count = 0

        writer.writerow(_COLUMNS)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        for record in _iter_records(db, label, date_from, date_to):
            writer.writerow(_record_row(record))
            count += 1
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

        logger.info(
            "GET /report/export/csv | user=%s | rows=%d | "
            "processing_time=%.3f sec",
            current_user.username,
            count,
            time.perf_counter() - start,
        )

    return StreamingResponse(
        stream(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                f'attachment; filename="{_export_filename("csv")}"'
        },
    )


@router.get("/report/export/excel")
def export_excel(
    request: Request,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    label: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Mengekspor riwayat deteksi sebagai Excel (.xlsx) di memori,
    tanpa file permanen."""
    start = time.perf_counter()

    # write_only: hemat memori untuk jumlah baris besar.
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet(title="Riwayat Deteksi")
    sheet.append(list(_COLUMNS))

    count = 0
    for record in _iter_records(db, label, date_from, date_to):
        sheet.append(_record_row(record))
        count += 1

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    logger.info(
        "GET /report/export/excel | user=%s | rows=%d | "
        "processing_time=%.3f sec",
        current_user.username,
        count,
        time.perf_counter() - start,
    )

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                f'attachment; filename="{_export_filename("xlsx")}"'
        },
    )