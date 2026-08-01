"""Model ORM User untuk autentikasi."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """Akun pengguna aplikasi Deteksi Tanaman Melon."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="admin", server_default="admin"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<User(username={self.username!r}, role={self.role!r})>"