"""Schema Pydantic v2 untuk autentikasi dan data user."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Body POST /auth/login. Field username menerima username ATAU
    email."""

    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class UserResponse(BaseModel):
    """Data user yang aman diekspos (tanpa password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class LoginResponse(BaseModel):
    """Response POST /auth/login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse