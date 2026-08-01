"""Skrip pengujian CRUD DetectionResult.

Jalankan dari folder backend/:
    python test_crud.py

Alur: koneksi -> insert 2 dummy -> tampilkan semua -> update 1 ->
delete 1 -> tampilkan hasil akhir.
"""

import sys

from sqlalchemy.orm import Session

from app.crud.detection_crud import (
    create_detection,
    delete_detection,
    get_all_detections,
    get_detection_by_id,
    update_detection,
)
from app.db.base import Base
from app.db.database import engine
from app.db.session import SessionLocal
from app.models import DetectionResult
from app.schemas.detection import DetectionCreate, DetectionResponse


def print_detection(row: DetectionResult) -> None:
    """Menampilkan satu record dalam format ringkas dan rapi."""
    response = DetectionResponse.model_validate(row)
    print(
        f"    - id={response.id}\n"
        f"      label={response.label} | action={response.action}\n"
        f"      image={response.image_path}\n"
        f"      detected_at={response.detected_at} | "
        f"updated_at={response.updated_at}"
    )


def show_all(db: Session, title: str) -> None:
    """Menampilkan seluruh record dengan judul section."""
    results = get_all_detections(db)
    print(f"\n=== {title} (total: {len(results)}) ===")
    for row in results:
        print_detection(row)


def main() -> int:
    """Menjalankan seluruh alur pengujian CRUD."""
    print("[1] Menyiapkan koneksi database dan tabel ...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        print("[2] Insert 2 data dummy ...")
        first = create_detection(
            db,
            DetectionCreate(
                image_path="uploads/melon_001.jpg",
                annotated_image_path="annotated/melon_001_annotated.jpg",
                label="daun_melon",
                action="pangkas",
            ),
        )
        second = create_detection(
            db,
            DetectionCreate(
                image_path="uploads/melon_002.jpg",
                annotated_image_path=None,
                label="daun_sehat",
                action="aman",
            ),
        )
        print(f"    Insert OK: {first.id}")
        print(f"    Insert OK: {second.id}")

        show_all(db, "SELURUH DATA SETELAH INSERT")

        print("\n[3] Update data pertama (label & action) ...")
        updated = update_detection(
            db,
            first.id,
            {"label": "daun_melon_revisi", "action": "pangkas_segera"},
        )
        if updated is None:
            raise RuntimeError("Update gagal: record tidak ditemukan.")
        print("    Update OK:")
        print_detection(updated)

        print("\n[4] Delete data kedua ...")
        deleted = delete_detection(db, second.id)
        print(f"    Delete OK: {deleted}")

        check = get_detection_by_id(db, second.id)
        print(f"    Verifikasi get_detection_by_id (harus None): {check}")

        show_all(db, "HASIL AKHIR")

        print("\n[OK] Pengujian CRUD DetectionResult BERHASIL")
        return 0
    except Exception as exc:  # noqa: BLE001
        print("\n[GAGAL] Pengujian CRUD GAGAL")
        print(f"Detail error: {exc}")
        return 1
    finally:
        db.close()
        print("[5] Session ditutup.")


if __name__ == "__main__":
    sys.exit(main())