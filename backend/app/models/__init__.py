"""Registrasi seluruh model ORM agar dikenali oleh Base.metadata."""

from app.models.detection_result import DetectionResult
from app.models.user import User

__all__ = ["DetectionResult", "User"]