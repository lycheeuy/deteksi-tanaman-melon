"""Stress test POST /api/esp32/detect — 20 upload berturut-turut
(Phase 38A revisi).

Dua mode:

1) MODE TEST (default) — 20 upload via TestClient (tanpa server,
   tanpa model, PostgreSQL tidak disentuh):

       python test_esp32_stress.py

2) MODE LIVE — 20 upload ke server yang SEDANG BERJALAN (model &
   database asli) — menirukan ESP32 yang mengirim beruntun:

       python test_esp32_stress.py --live
       python test_esp32_stress.py --live --url http://192.168.1.10:8000
"""

import statistics
import sys
import time
from pathlib import Path

# Pakai ulang helper simulator (stub TF ikut aktif saat diimpor).
from test_esp32_api import make_jpeg, post_multipart  # noqa: E402

TOTAL_UPLOADS = 20

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


def summarize(durations: list[float]) -> str:
    """Ringkasan durasi per-request dalam milidetik."""
    return (
        f"avg {statistics.mean(durations) * 1000:.0f} ms | "
        f"min {min(durations) * 1000:.0f} ms | "
        f"maks {max(durations) * 1000:.0f} ms"
    )


def run_stress_testclient() -> int:
    """20 upload berturut-turut via TestClient (deteksi di-stub)."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    import app.models  # noqa: F401
    from app.api import detection as det_api
    from app.db.session import get_db
    from app.main import app
    from app.services.history_service import HistoryService

    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, future=True)
    shared_db = TestSession()

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    class FakeDetection:
        def detect_image(self, path):
            return {
                "image_path": str(path),
                "total_detection": 1,
                "detections": [
                    {"class_id": 0, "label": "Tunas Air",
                     "confidence": 0.95, "grid_x": 4, "grid_y": 3}
                ],
            }

    fake = FakeDetection()
    history = HistoryService(detection_service=fake)

    class HistoryOnSharedDb:
        def save_detection_result(
            self, image_path, detection_result, annotated_image_path=None
        ):
            return history.save_detection_result(
                image_path,
                detection_result,
                annotated_image_path=annotated_image_path,
                db=shared_db,
            )

    app.dependency_overrides[det_api.get_detection_service] = lambda: fake
    app.dependency_overrides[det_api.get_history_service] = (
        lambda: HistoryOnSharedDb()
    )

    client = TestClient(app)
    jpeg = make_jpeg()

    before = client.get("/dashboard/summary").json()["total_detection"]

    statuses: list[int] = []
    record_ids: list[str] = []
    request_ids: list[str] = []
    durations: list[float] = []
    paths: list[str] = []

    print(f"\nMengirim {TOTAL_UPLOADS} upload berturut-turut ...")
    for index in range(TOTAL_UPLOADS):
        started = time.perf_counter()
        response = client.post(
            "/api/esp32/detect",
            files={"image": (f"snap_{index}.jpg", jpeg, "image/jpeg")},
            headers={"X-Device-Id": "esp32-stress"},
        )
        durations.append(time.perf_counter() - started)
        statuses.append(response.status_code)
        if response.status_code == 200:
            payload = response.json()
            record_ids.append(payload["record_id"])
            request_ids.append(payload["request_id"])
            paths.extend([payload["annotated_image"]])

    after = client.get("/dashboard/summary").json()["total_detection"]

    print(f"\n[1] Hasil {TOTAL_UPLOADS} upload")
    check(f"semua {TOTAL_UPLOADS} response 200",
          statuses.count(200) == TOTAL_UPLOADS,
          f"200 sebanyak {statuses.count(200)}/{TOTAL_UPLOADS}")
    check("record_id semuanya unik",
          len(set(record_ids)) == TOTAL_UPLOADS)
    check("request_id semuanya unik",
          len(set(request_ids)) == TOTAL_UPLOADS)
    check(f"total_detection bertambah {TOTAL_UPLOADS}",
          after == before + TOTAL_UPLOADS, f"{before} -> {after}")
    print(f"  [INFO ] durasi per-request: {summarize(durations)}")

    # Bersih-bersih file hasil stress test.
    recent = client.get(
        "/dashboard/recent?limit=20").json()["items"]
    for record in recent:
        for key in ("image_path", "annotated_image_path"):
            if record.get(key):
                Path(record[key]).unlink(missing_ok=True)
    shared_db.close()

    print(f"\n=== HASIL: {PASS} lolos, {FAIL} gagal ===")
    return 0 if FAIL == 0 else 1


def run_stress_live(base_url: str) -> int:
    """20 upload beruntun ke server berjalan (model & DB asli)."""
    endpoint = f"{base_url.rstrip('/')}/api/esp32/detect"
    jpeg = make_jpeg()
    print(f"Mengirim {TOTAL_UPLOADS} upload ke {endpoint} ...")

    ok_count = 0
    request_ids: list[str] = []
    durations: list[float] = []
    for index in range(TOTAL_UPLOADS):
        started = time.perf_counter()
        status_code, payload = post_multipart(
            endpoint, "image", f"stress_{index}.jpg", jpeg, "image/jpeg"
        )
        durations.append(time.perf_counter() - started)
        if status_code == 200 and payload.get("success"):
            ok_count += 1
            request_ids.append(payload["request_id"])
        print(f"  #{index + 1:02d} HTTP {status_code} "
              f"({durations[-1] * 1000:.0f} ms)")

    print(f"\nBerhasil {ok_count}/{TOTAL_UPLOADS} | "
          f"request_id unik: {len(set(request_ids))} | "
          f"{summarize(durations)}")
    print("Dashboard: Total/Today/Recent History bertambah otomatis.")
    return 0 if ok_count == TOTAL_UPLOADS else 1


if __name__ == "__main__":
    if "--live" in sys.argv:
        url = "http://localhost:8000"
        if "--url" in sys.argv:
            url = sys.argv[sys.argv.index("--url") + 1]
        sys.exit(run_stress_live(url))
    sys.exit(run_stress_testclient())