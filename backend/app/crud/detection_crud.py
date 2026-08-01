"""Operasi CRUD untuk model DetectionResult (SQLAlchemy 2.x ORM)."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import DetectionResult
from app.schemas.detection import DetectionCreate

# Kolom yang boleh diperbarui melalui update_detection.
_UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {"image_path", "annotated_image_path", "label", "action", "detected_at"}
)

# Batas pagination untuk get_all_detections.
_MIN_LIMIT: int = 1
_MAX_LIMIT: int = 1000
_MIN_OFFSET: int = 0


def create_detection(db: Session, detection: DetectionCreate) -> DetectionResult:
    """Menyimpan satu record hasil deteksi baru.

    Args:
        db: Session SQLAlchemy aktif.
        detection: Data input tervalidasi (schema DetectionCreate).

    Returns:
        DetectionResult: Record yang baru tersimpan (sudah di-refresh).

    Raises:
        Exception: Diteruskan kembali setelah rollback jika commit gagal.
    """
    db_detection = DetectionResult(
        **detection.model_dump(exclude_none=True)
    )
    try:
        db.add(db_detection)
        db.commit()
        db.refresh(db_detection)
    except Exception:
        db.rollback()
        raise
    return db_detection


def get_detection_by_id(
    db: Session, detection_id: uuid.UUID
) -> DetectionResult | None:
    """Mengambil satu record berdasarkan primary key.

    Returns:
        DetectionResult | None: Record jika ditemukan, selain itu None.
    """
    return db.get(DetectionResult, detection_id)


def get_all_detections(
    db: Session, limit: int = 100, offset: int = 0
) -> list[DetectionResult]:
    """Mengambil daftar record dengan pagination tervalidasi.

    Args:
        db: Session SQLAlchemy aktif.
        limit: Jumlah maksimal record (minimal 1, maksimal 1000).
        offset: Jumlah record yang dilewati (minimal 0).

    Returns:
        list[DetectionResult]: Daftar record, terbaru lebih dulu.

    Raises:
        ValueError: Jika limit atau offset di luar batas yang diizinkan.
    """
    if limit < _MIN_LIMIT or limit > _MAX_LIMIT:
        raise ValueError(
            f"limit harus antara {_MIN_LIMIT} dan {_MAX_LIMIT}, "
            f"diterima: {limit}"
        )
    if offset < _MIN_OFFSET:
        raise ValueError(
            f"offset harus >= {_MIN_OFFSET}, diterima: {offset}"
        )

    stmt = (
        select(DetectionResult)
        .order_by(DetectionResult.detected_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all())


def count_detections(db: Session) -> int:
    """Menghitung seluruh record hasil deteksi.

    Returns:
        int: Total record pada tabel detection_results.
    """
    stmt = select(func.count()).select_from(DetectionResult)
    return int(db.execute(stmt).scalar_one())


def count_detections_today(db: Session) -> int:
    """Menghitung record deteksi dengan detected_at pada hari ini
    (berdasarkan tanggal server database).

    Returns:
        int: Jumlah record hari ini.
    """
    stmt = (
        select(func.count())
        .select_from(DetectionResult)
        .where(func.date(DetectionResult.detected_at) == func.current_date())
    )
    return int(db.execute(stmt).scalar_one())


def update_detection(
    db: Session, detection_id: uuid.UUID, data: dict[str, Any]
) -> DetectionResult | None:
    """Memperbarui sebagian field dari satu record (partial update).

    Hanya field pada _UPDATABLE_FIELDS yang diterapkan; key lain diabaikan.

    Returns:
        DetectionResult | None: Record terbaru jika ditemukan, selain itu None.

    Raises:
        Exception: Diteruskan kembali setelah rollback jika commit gagal.
    """
    db_detection = db.get(DetectionResult, detection_id)
    if db_detection is None:
        return None

    try:
        for field, value in data.items():
            if field in _UPDATABLE_FIELDS:
                setattr(db_detection, field, value)
        db.commit()
        db.refresh(db_detection)
    except Exception:
        db.rollback()
        raise
    return db_detection


def delete_detection(db: Session, detection_id: uuid.UUID) -> bool:
    """Menghapus satu record berdasarkan primary key.

    Returns:
        bool: True jika record ditemukan dan terhapus, False jika tidak ada.

    Raises:
        Exception: Diteruskan kembali setelah rollback jika commit gagal.
    """
    db_detection = db.get(DetectionResult, detection_id)
    if db_detection is None:
        return False

    try:
        db.delete(db_detection)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


# Label khusus untuk record tanpa deteksi (selaras HistoryService).
NO_DETECTION_LABEL: str = "No Detection"


def count_no_detection(db: Session) -> int:
    """Menghitung record dengan label "No Detection".

    Returns:
        int: Jumlah record tanpa deteksi.
    """
    stmt = (
        select(func.count())
        .select_from(DetectionResult)
        .where(DetectionResult.label == NO_DETECTION_LABEL)
    )
    return int(db.execute(stmt).scalar_one())


def count_detections_by_label(db: Session) -> list[tuple[str, int]]:
    """Menghitung jumlah record per label.

    Returns:
        list[tuple[str, int]]: Pasangan (label, jumlah), terurut
        jumlah menurun.
    """
    stmt = (
        select(DetectionResult.label, func.count())
        .group_by(DetectionResult.label)
        .order_by(func.count().desc())
    )
    return [(str(label), int(count)) for label, count in db.execute(stmt)]


def search_detections(
    db: Session,
    *,
    search: str | None = None,
    label: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[DetectionResult], int]:
    """Mencari record riwayat dengan filter dan pagination.

    Args:
        search: Teks bebas (dicocokkan ke label dan image_path).
        label: Filter label persis.
        date_from: Batas bawah tanggal detected_at (inklusif).
        date_to: Batas atas tanggal detected_at (inklusif).
        limit: Jumlah record per halaman.
        offset: Jumlah record yang dilewati.

    Returns:
        tuple: (daftar record terurut terbaru, total record cocok).
    """
    conditions = []
    if search:
        pattern = f"%{search}%"
        conditions.append(
            or_(
                DetectionResult.label.ilike(pattern),
                DetectionResult.image_path.ilike(pattern),
            )
        )
    if label:
        conditions.append(DetectionResult.label == label)
    if date_from:
        conditions.append(
            func.date(DetectionResult.detected_at) >= date_from
        )
    if date_to:
        conditions.append(func.date(DetectionResult.detected_at) <= date_to)

    total_stmt = select(func.count()).select_from(DetectionResult)
    items_stmt = select(DetectionResult)
    if conditions:
        total_stmt = total_stmt.where(*conditions)
        items_stmt = items_stmt.where(*conditions)

    total = int(db.execute(total_stmt).scalar_one())
    items = list(
        db.execute(
            items_stmt.order_by(DetectionResult.detected_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return items, total