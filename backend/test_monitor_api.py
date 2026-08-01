"""Unit test endpoint GET /monitor (Phase 37 revisi).

Jalankan dari folder backend/ (venv aktif):

    python test_monitor_api.py

Aman: database SQLite in-memory (PostgreSQL tidak disentuh),
TensorFlow di-stub bila tidak terpasang. Butuh psutil.
"""

import sys
import types

# --- Stub TensorFlow bila tidak terpasang ---
try:  # noqa: SIM105
    import tensorflow  # noqa: F401
except ImportError:
    tf_stub = types.ModuleType("tensorflow")
    tf_stub.lite = types.SimpleNamespace(Interpreter=object)
    tf_stub.__version__ = "stub"
    sys.modules["tensorflow"] = tf_stub

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402,F401
from app.models import User  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    """Mencetak hasil satu pengecekan dan mencatat statistik."""
    global PASS, FAIL  # noqa: PLW0603
    ok = "LOLOS" if condition else "GAGAL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{ok}] {name}" + (f" | {detail}" if detail else ""))


def main() -> int:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, future=True)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    db = TestSession()
    db.add(
        User(
            username="admin_test",
            email="admin_test@melon.local",
            password_hash=hash_password("admin123"),
            full_name="Admin Test",
        )
    )
    db.commit()
    db.close()

    token = client.post(
        "/auth/login",
        json={"username": "admin_test", "password": "admin123"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # ============ [1] Proteksi autentikasi ============
    print("\n[1] Proteksi autentikasi")
    check("tanpa token -> 401", client.get("/monitor").status_code == 401)
    check(
        "token rusak -> 401",
        client.get("/monitor", headers={"Authorization": "Bearer x"})
        .status_code == 401,
    )

    # ============ [2] Kontrak response ============
    print("\n[2] Kontrak response")
    r = client.get("/monitor", headers=headers)
    d = r.json()
    check("status 200", r.status_code == 200)

    expected_keys = (
        "backend", "app_version", "build_time", "model_name",
        "environment", "database", "model", "cpu", "memory", "disk",
        "latency_ms", "uptime_seconds", "last_update",
    )
    missing = [key for key in expected_keys if key not in d]
    check("13 field lengkap", not missing,
          f"kurang: {missing}" if missing else "semua ada")

    # ============ [3] Field baru (revisi) ============
    print("\n[3] Field baru")
    check("app_version sesuai settings",
          d["app_version"] == settings.APP_VERSION,
          f"nilai={d['app_version']}")
    check("environment sesuai APP_ENV",
          d["environment"] == settings.APP_ENV,
          f"nilai={d['environment']}")
    check("environment valid",
          d["environment"] in ("development", "production", "staging"))
    check("build_time terisi (ISO)",
          isinstance(d["build_time"], str) and "T" in d["build_time"],
          d["build_time"])
    expected_model = (
        settings.MODEL_PATH.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        if settings.MODEL_PATH else "-"
    )
    check("model_name = nama file MODEL_PATH",
          d["model_name"] == expected_model,
          f"nilai={d['model_name']}")

    # ============ [4] Nilai resource masuk akal ============
    print("\n[4] Nilai resource")
    check("cpu 0-100", 0 <= d["cpu"]["percent"] <= 100)
    check("ram 0-100 + total > 0",
          0 <= d["memory"]["percent"] <= 100
          and d["memory"]["total_mb"] > 0)
    check("disk 0-100 + total > 0",
          0 <= d["disk"]["percent"] <= 100 and d["disk"]["total_gb"] > 0)
    check("database connected", d["database"] == "connected")
    check("uptime >= 0", d["uptime_seconds"] >= 0)
    check("latency_ms > 0", d["latency_ms"] > 0)

    print(f"\n=== HASIL: {PASS} lolos, {FAIL} gagal ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())