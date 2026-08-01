"""Model ORM DetectionResult untuk tabel detection_results."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DetectionResult(Base):
    """Merepresentasikan satu hasil deteksi tanaman melon dari ESP32-CAM."""

    __tablename__ = "detection_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary key UUID",
    )
    image_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Path gambar asli hasil capture",
    )
    annotated_image_path: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Path gambar dengan anotasi bounding box",
    )
    label: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Label hasil klasifikasi model AI",
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Rekomendasi aksi dari rule engine (mis. pangkas/aman)",
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Waktu deteksi dilakukan",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Waktu record dibuat",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Waktu record terakhir diperbarui",
    )

    def __repr__(self) -> str:
        return (
            f"<DetectionResult(id={self.id!s}, label={self.label!r}, "
            f"action={self.action!r}, detected_at={self.detected_at})>"
        )