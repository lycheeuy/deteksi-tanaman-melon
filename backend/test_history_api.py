"""Test suite endpoint History API (Phase 35).

Jalankan dari folder backend/ (venv aktif):

    python test_history_api.py

Aman dijalankan di mesin mana pun:
- Database memakai SQLite in-memory (PostgreSQL Anda TIDAK disentuh).
- TensorFlow di-stub otomatis bila tidak terpasang.
- File gambar uji dibuat sementara lalu dibersihkan.

Cakupan: GET /history (list, pagination, search, filter label,
filter tanggal), DELETE tunggal (+404), bulk delete (+401 tanpa
token, batas 100 id -> 422).
"""

import sys
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Stub TensorFlow bila tidak terpasang (agar app.main bisa impor) ---
try:  # noqa: SIM105
    import tensorflow  # noqa: F401
except ImportError:
    tf_stub = types.ModuleType("tensorflow")
    tf_stub.lite = types.SimpleNamespace(Interpreter=object)
    tf_stub.__version__ = "stub"
    sys.modules["tensorflow"] = tf_stub

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402,F401  (registrasi model)
from app.models import DetectionResult, User  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    """Mencetak hasil satu pengecekan dan mencatat statistik."""
    global PASS, FAIL  # noqa: PLW0603
    status = "LOLOS" if condition else "GAGAL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    suffix = f" | {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def main() -> int:
    # --- Database uji: SQLite in-memory (lintas-thread utk TestClient) ---
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

    # --- Seed: 1 admin + 7 record beragam label & tanggal ---
    now = datetime.now(timezone.utc)
    seed = [
        ("Tunas Air", 0),
        ("Tunas Air", 1),
        ("Tunas Air", 2),
        ("Buah Siap", 3),
        ("Buah Siap", 4),
        ("Daun Siap", 30),   # sebulan lalu
        ("No Detection", 31),
    ]
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    created_files: list[Path] = []
    ids: list[str] = []

    db = TestSession()
    db.add(
        User(
            username="admin_test",
            email="admin_test@melon.local",
            password_hash=hash_password("admin123"),
            full_name="Admin Test",
        )
    )
    for i, (label, days_ago) in enumerate(seed):
        file_path = upload_dir / f"test_history_{i}.jpg"
        file_path.write_bytes(b"\xff\xd8\xff\xe0TEST")
        created_files.append(file_path)
        record = DetectionResult(
            image_path=file_path.as_posix(),
            label=label,
            action="None",
            detected_at=now - timedelta(days=days_ago),
        )
        db.add(record)
        db.flush()
        ids.append(str(record.id))
    db.commit()
    db.close()

    token = client.post(
        "/auth/login",
        json={"username": "admin_test", "password": "admin123"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # ================= [1] Autentikasi =================
    print("\n[1] Proteksi autentikasi")
    check("GET /history tanpa token -> 401",
          client.get("/history").status_code == 401)
    check(
        "DELETE bulk tanpa token -> 401",
        client.request("DELETE", "/history", json={"ids": ids[:1]})
        .status_code == 401,
    )

    # ================= [2] List & pagination =================
    print("\n[2] List & pagination")
    r = client.get("/history?page=1&page_size=3", headers=headers)
    d = r.json()
    check("GET /history -> 200", r.status_code == 200)
    check("total = 7", d["total"] == 7, f"total={d['total']}")
    check("total_pages = 3", d["total_pages"] == 3)
    check("halaman 1 berisi 3 item", len(d["items"]) == 3)
    check(
        "urut detected_at menurun",
        d["items"][0]["detected_at"] >= d["items"][-1]["detected_at"],
    )
    r3 = client.get("/history?page=3&page_size=3", headers=headers)
    check("halaman 3 berisi 1 item", len(r3.json()["items"]) == 1)

    # ================= [3] Search & filter =================
    print("\n[3] Search & filter")
    r = client.get("/history?search=tunas", headers=headers)
    check("search 'tunas' -> 3", r.json()["total"] == 3,
          f"total={r.json()['total']}")

    r = client.get("/history?label=Buah%20Siap", headers=headers)
    check("filter label exact -> 2", r.json()["total"] == 2)

    date_from = (now - timedelta(days=5)).date().isoformat()
    r = client.get(f"/history?date_from={date_from}", headers=headers)
    check("filter date_from (5 hari) -> 5", r.json()["total"] == 5,
          f"total={r.json()['total']}")

    date_to = (now - timedelta(days=10)).date().isoformat()
    r = client.get(f"/history?date_to={date_to}", headers=headers)
    check("filter date_to (>=10 hari lalu) -> 2", r.json()["total"] == 2)

    r = client.get(
        f"/history?search=tunas&date_from={date_from}", headers=headers
    )
    check("kombinasi search + tanggal -> 3", r.json()["total"] == 3)

    # ================= [4] Delete tunggal =================
    print("\n[4] Delete tunggal")
    target = ids[0]
    r = client.delete(f"/history/{target}", headers=headers)
    check("DELETE record -> 200", r.status_code == 200)
    check("file gambar ikut terhapus", not created_files[0].exists())
    check(
        "record hilang dari list",
        client.get("/history", headers=headers).json()["total"] == 6,
    )
    r = client.delete(f"/history/{uuid.uuid4()}", headers=headers)
    check("id tak dikenal -> 404", r.status_code == 404)

    # ================= [5] Bulk delete =================
    print("\n[5] Bulk delete")
    r = client.request(
        "DELETE", "/history", headers=headers, json={"ids": ids[1:3]}
    )
    d = r.json()
    check("bulk 2 id -> deleted=2", r.status_code == 200 and d["deleted"] == 2)
    check(
        "file kedua record terhapus",
        not created_files[1].exists() and not created_files[2].exists(),
    )
    r = client.request(
        "DELETE", "/history", headers=headers,
        json={"ids": [str(uuid.uuid4())]},
    )
    check("id asing -> deleted=0, not_found=1",
          r.json()["deleted"] == 0 and r.json()["not_found"] == 1)
    r = client.request(
        "DELETE", "/history", headers=headers,
        json={"ids": [str(uuid.uuid4()) for _ in range(101)]},
    )
    check("lebih dari 100 id -> 422", r.status_code == 422)

    # --- Bersih-bersih file uji yang tersisa ---
    for path in created_files:
        path.unlink(missing_ok=True)

    print(f"\n=== HASIL: {PASS} lolos, {FAIL} gagal ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())