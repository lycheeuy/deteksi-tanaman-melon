"""Router autentikasi: login dan profil user saat ini."""

import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.schemas.user import LoginRequest, LoginResponse, UserResponse
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login(
    request: Request, body: LoginRequest, db: Session = Depends(get_db)
) -> LoginResponse:
    """Login dengan username ATAU email + password.

    Returns:
        LoginResponse: access_token (JWT bearer) dan data user.

    Raises:
        HTTPException: 401 bila kredensial salah / akun nonaktif.
    """
    start = time.perf_counter()
    user = authenticate_user(db, body.username, body.password)
    if user is None:
        logger.warning(
            "Login GAGAL | client_ip=%s | identitas=%s",
            request.client.host if request.client else "-",
            body.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah.",
        )

    token = create_access_token(user.id)
    logger.info(
        "Login BERHASIL | client_ip=%s | username=%s | "
        "processing_time=%.3f sec",
        request.client.host if request.client else "-",
        user.username,
        time.perf_counter() - start,
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/auth/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Profil user yang sedang login (contoh endpoint terproteksi)."""
    return UserResponse.model_validate(current_user)