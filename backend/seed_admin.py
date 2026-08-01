"""Seed akun admin default (jalankan sekali dari folder backend/).

    python seed_admin.py

Membuat akun admin/admin123 bila belum ada. Password di-hash bcrypt.
"""

import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base
from app.db.database import engine
from app.db.session import SessionLocal
from app.models import User  # registrasi model


def main() -> int:
    """Membuat tabel users (bila belum ada) dan akun admin default."""
    print("[1] Menyiapkan tabel ...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.execute(
            select(User).where(User.username == "admin")
        ).scalar_one_or_none()
        if existing is not None:
            print("[2] Akun 'admin' sudah ada — tidak ada yang dibuat.")
            return 0

        print("[2] Membuat akun admin default ...")
        admin = User(
            username="admin",
            email="admin@melon.local",
            password_hash=hash_password("admin123"),
            full_name="Administrator",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("    username : admin")
        print("    email    : admin@melon.local")
        print("    password : admin123  (SEGERA ganti di production)")
        print("\n[OK] Seed admin BERHASIL")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())