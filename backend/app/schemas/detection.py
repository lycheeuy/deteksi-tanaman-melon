"""Schema Pydantic v2 untuk data hasil deteksi tanaman melon."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DetectionCreate(BaseModel):
    """Schema input untuk membuat record hasil deteksi baru."""

    image_path: str = Field(
        ...,
        max_length=255,
        description="Path gambar asli hasil capture",
    )
    annotated_image_path: str | None = Field(
        default=None,
        max_length=255,
        description="Path gambar dengan anotasi bounding box",
    )
    label: str = Field(
        ...,
        max_length=50,
        description="Label hasil klasifikasi model AI",
    )
    action: str = Field(
        ...,
        max_length=100,
        description="Rekomendasi aksi dari rule engine",
    )
    detected_at: datetime | None = Field(
        default=None,
        description="Waktu deteksi (opsional, default waktu server)",
    )


class DetectionResponse(BaseModel):
    """Schema output untuk mengembalikan record hasil deteksi."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_path: str
    annotated_image_path: str | None
    label: str
    action: str
    detected_at: datetime
    created_at: datetime
    updated_at: datetime