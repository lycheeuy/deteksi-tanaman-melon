"""Base class deklaratif untuk seluruh model ORM SQLAlchemy 2.x."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class yang akan diwarisi oleh seluruh model di app/models/.

    Catatan: registrasi model ke Base.metadata dilakukan melalui
    app/models/__init__.py. Pastikan `app.models` sudah ter-import
    sebelum memanggil Base.metadata.create_all().
    """

    pass