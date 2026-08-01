"""Utilitas keamanan: hashing password dengan bcrypt (passlib)."""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Meng-hash password dengan bcrypt.

    Returns:
        str: Hash bcrypt (aman disimpan di database).
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Memverifikasi password terhadap hash tersimpan.

    Returns:
        bool: True bila cocok.
    """
    return pwd_context.verify(plain_password, password_hash)