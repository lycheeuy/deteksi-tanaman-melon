"""Skrip pengujian ORM DetectionResult.

Jalankan dari folder backend/:
    python test_model.py

Alur: create_all() -> insert data dummy -> query kembali -> tampilkan
hasil -> tutup session.
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.database import engine
from app.db.session import SessionLocal
from app.models import DetectionResult
from app.schemas.detection import DetectionResponse


def create_tables() -> None:
    """Membuat seluruh tabel yang terdaftar pada Base.metadata."""
    print("[1] Membuat tabel via Base.metadata.create_all() ...")
    Base.metadata.create_all(bind=engine)
    print("    Tabel 'detection_results' siap.")


def insert_dummy(db: Session) -> DetectionResult:
    """Menyisipkan satu data dummy hasil deteksi.

    Args:
        db: Session SQLAlchemy aktif.

    Returns:
        DetectionResult: Record yang baru tersimpan.
    """
    print("[2] Insert 1 data dummy ...")
    dummy = DetectionResult(
        image_path="uploads/dummy_melon.jpg",
        annotated_image_path="annotated/dummy_melon_annotated.jpg",
        label="daun_melon",
        action="pangkas",
    )
    db.add(dummy)
    db.commit()
    db.refresh(dummy)
    print(f"    Tersimpan dengan id: {dummy.id}")
    return dummy


def query_results(db: Session) -> None:
    """Mengambil kembali seluruh data dan menampilkannya."""
    print("[3] Query kembali data dari tabel detection_results ...")
    results = db.execute(select(DetectionResult)).scalars().all()
    print(f"    Total record: {len(results)}")
    for row in results:
        response = DetectionResponse.model_validate(row)
        print("-" * 50)
        print(f"    id                   : {response.id}")
        print(f"    image_path           : {response.image_path}")
        print(f"    annotated_image_path : {response.annotated_image_path}")
        print(f"    label                : {response.label}")
        print(f"    action               : {response.action}")
        print(f"    detected_at          : {response.detected_at}")
        print(f"    created_at           : {response.created_at}")
        print(f"    updated_at           : {response.updated_at}")


def main() -> int:
    """Menjalankan seluruh alur pengujian ORM."""
    try:
        create_tables()
        db: Session = SessionLocal()
        try:
            insert_dummy(db)
            query_results(db)
        finally:
            db.close()
            print("[4] Session ditutup.")
        print("\n[OK] Pengujian ORM DetectionResult BERHASIL")
        return 0
    except Exception as exc:  # noqa: BLE001
        print("\n[GAGAL] Pengujian ORM GAGAL")
        print(f"Detail error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())