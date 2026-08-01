"""Auth Service: autentikasi user, JWT, dan dependency get_current_user."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import verify_password
from app.db.session import get_db
from app.models import User

logger = logging.getLogger(__name__)

JWT_ALGORITHM: str = "HS256"

# auto_error=False agar kita mengembalikan 401 (bukan 403 bawaan)
# saat header Authorization tidak ada.
_bearer_scheme = HTTPBearer(auto_error=False)


def authenticate_user(
    db: Session, username_or_email: str, password: str
) -> User | None:
    """Memverifikasi kredensial user (username ATAU email + password).

    Returns:
        User | None: User bila kredensial benar dan akun aktif,
        selain itu None.
    """
    stmt = select(User).where(
        or_(
            User.username == username_or_email,
            User.email == username_or_email,
        )
    )
    user = db.execute(stmt).scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def create_access_token(user_id: uuid.UUID) -> str:
    """Membuat JWT dengan subject id user dan masa berlaku dari
    settings.

    Returns:
        str: Token JWT ter-encode.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    """Mendekode dan memvalidasi JWT (tanda tangan + kedaluwarsa).

    Returns:
        dict | None: Payload bila valid, None bila tidak.
    """
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency FastAPI: mengembalikan user dari header
    Authorization Bearer. Pakai untuk memproteksi endpoint sensitif.

    Raises:
        HTTPException: 401 bila token tidak ada/tidak valid/user
            tidak aktif.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tidak terautentikasi.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    payload = verify_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise unauthorized

    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except ValueError as exc:
        raise unauthorized from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user