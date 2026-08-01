"""Pengelolaan session database dan dependency injection FastAPI."""

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.database import engine

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency FastAPI yang menyediakan session database per-request.

    Yields:
        Session: Session SQLAlchemy aktif.

    Session selalu ditutup setelah request selesai, baik sukses maupun error.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()