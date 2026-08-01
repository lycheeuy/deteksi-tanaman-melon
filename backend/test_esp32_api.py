"""Simulator ESP32 + test suite POST /api/esp32/detect (Phase 38A).

Dua mode:

1) MODE TEST (default) — validasi kontrak endpoint tanpa server:

       python test_esp32_api.py

   Database SQLite in-memory (PostgreSQL tidak disentuh); pipeline
   deteksi di-stub agar tidak butuh model.

2) MODE LIVE — bertindak sebagai "ESP32 palsu" yang mengirim snapshot
   ke server yang SEDANG BERJALAN (uvicorn), memakai model & database
   asli — cocok untuk melihat dashboard ter-update otomatis:

       python test_esp32_api.py --live
       python test_esp32_api.py --live --url http://192.168.1.10:8000

   Buka dashboard di browser: Total/Today/Recent History bertambah
   dalam <=30 detik (auto-refresh) tanpa menyentuh frontend.
"""

import io
import json
import sys
import types
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import cv2
import numpy as np

# --- Stub TensorFlow bila tidak terpasang (mode test) ---
try:  # noqa: SIM105
    import tensorflow  # noqa: F401
except ImportError:
    tf_stub = types.ModuleType("tensorflow")
    tf_stub.lite = types.SimpleNamespace(Interpreter=object)
    tf_stub.__version__ = "stub"
    sys.modules["tensorflow"] = tf_stub

PASS = 0
FAIL = 0

RESPONSE_KEYS = ("success", "label", "total_detection", "record_id",
                 "annotated_image", "device", "request_id")


def check(name: str, condition: bool, detail: str = "") -> None:
    """Mencetak hasil satu pengecekan dan mencatat statistik."""
    global PASS, FAIL  # noqa: PLW0603
    ok = "LOLOS" if condition else "GAGAL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{ok}] {name}" + (f" | {detail}" if detail else ""))


def make_jpeg(width: int = 640, height: int = 480) -> bytes:
    """Membuat JPEG sintetis (pola sederhana) — pengganti kamera."""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (40, 90, 40)
    cv2.circle(image, (width // 2, height // 2), 90, (60, 180, 90), -1)
    ok, buffer = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Gagal meng-encode JPEG sintetis.")
    return buffer.tobytes()


# =====================================================================
# MODE LIVE — kirim multipart ke server berjalan (stdlib, tanpa deps).
# =====================================================================
def post_multipart(
    url: str, field: str, filename: str, content: bytes,
    content_type: str, timeout: float = 15.0,
) -> tuple[int, dict]:
    """POST multipart/form-data satu file memakai urllib (stdlib)."""
    boundary = f"----esp32sim{uuid.uuid4().hex}"
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(
        f'Content-Disposition: form-data; name="{field}"; '
        f'filename="{filename}"\r\n'.encode()
    )
    body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.write(content)
    body.write(f"\r\n--{boundary}--\r\n".encode())

    request = urllib.request.Request(
        url,
        data=body.getvalue(),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def run_live(base_url: str) -> int:
    """Mode ESP32 palsu: kirim satu snapshot ke server berjalan."""
    endpoint = f"{base_url.rstrip('/')}/api/esp32/detect"
    print(f"Mengirim snapshot sintetis ke {endpoint} (timeout 15 dtk) ...")
    status_code, payload = post_multipart(
        endpoint, "image", "esp32_sim.jpg", make_jpeg(), "image/jpeg"
    )
    print(f"HTTP {status_code}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if status_code == 200 and payload.get("success"):
        print(
            "\nBerhasil — buka dashboard: Total/Today/Recent History akan"
            " ter-update otomatis (auto-refresh <=30 dtk)."
        )
        return 0
    print("\nGagal — pastikan uvicorn berjalan dan model termuat.")
    return 1


# =====================================================================
# MODE TEST — kontrak endpoint via TestClient (tanpa server & model).
# =====================================================================
def run_tests() -> int:
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
        """Pipeline deteksi palsu — hasil deterministik utk test."""

        detections: list[dict] = [
            {"class_id": 0, "label": "Tunas Air", "confidence": 0.95,
             "grid_x": 4, "grid_y": 3}
        ]

        def detect_image(self, path):
            return {
                "image_path": str(path),
                "total_detection": len(self.detections),
                "detections": list(self.detections),
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

    def upload(content: bytes, filename: str = "snap.jpg",
               mime: str = "image/jpeg"):
        return client.post(
            "/api/esp32/detect",
            files={"image": (filename, content, mime)},
        )

    # ---------- [1] Upload valid ----------
    print("\n[1] Upload valid (ada deteksi)")
    r = upload(jpeg)
    d = r.json()
    check("status 200", r.status_code == 200)
    check("response konsisten 7 field (kontrak v1)",
          tuple(sorted(d.keys())) == tuple(sorted(RESPONSE_KEYS)),
          f"keys={sorted(d.keys())}")
    check("device default 'esp32-cam'", d["device"] == "esp32-cam")
    check("request_id terisi", bool(d["request_id"]))
    check("label deteksi teratas", d["label"] == "Tunas Air")
    check("record_id terisi", bool(d["record_id"]))
    check("annotated_image terisi & file ada",
          bool(d["annotated_image"]) and Path(d["annotated_image"]).is_file())

    # ---------- [2] Nol deteksi: response tetap konsisten ----------
    print("\n[2] Nol deteksi")
    fake.detections = []
    r = upload(jpeg)
    d = r.json()
    check("status 200", r.status_code == 200)
    check("field tetap 7 (konsisten)",
          tuple(sorted(d.keys())) == tuple(sorted(RESPONSE_KEYS)))
    check("label 'No Detection' + total 0",
          d["label"] == "No Detection" and d["total_detection"] == 0)
    check("record_id tetap terisi (riwayat tersimpan)",
          bool(d["record_id"]))
    fake.detections = list(FakeDetection.detections)

    # ---------- [2b] Identitas perangkat & request ----------
    print("\n[2b] Identitas perangkat & request")
    r1 = client.post(
        "/api/esp32/detect",
        files={"image": ("snap.jpg", jpeg, "image/jpeg")},
        headers={"X-Device-Id": "esp32-kebun-01"},
    )
    check("X-Device-Id kustom dihormati",
          r1.json()["device"] == "esp32-kebun-01")
    r2 = upload(jpeg)
    check("request_id unik antar-request",
          r1.json()["request_id"] != r2.json()["request_id"])

    # ---------- [3] Validasi upload ----------
    print("\n[3] Validasi upload")
    r = upload(jpeg, filename="snap.gif", mime="image/gif")
    check("ekstensi salah -> 400", r.status_code == 400,
          r.json().get("detail", ""))
    r = upload(jpeg, filename="snap.jpg", mime="application/octet-stream")
    check("MIME salah -> 400", r.status_code == 400)
    r = upload(b"", filename="snap.jpg")
    check("file kosong -> 400", r.status_code == 400)
    r = upload(b"x" * (10 * 1024 * 1024 + 1))
    check("lebih dari 10 MB -> 413", r.status_code == 413)
    r = upload(b"bukan-jpeg-asli" * 100)
    check("bukan gambar valid -> 400", r.status_code == 400)

    # ---------- [4] Dashboard ikut ter-update ----------
    print("\n[4] Dashboard auto-update (sumber data sama)")
    before = client.get("/dashboard/summary").json()["total_detection"]
    new_record_id = upload(jpeg).json()["record_id"]
    after_summary = client.get("/dashboard/summary").json()
    recent = client.get("/dashboard/recent").json()["items"]
    check("total_detection bertambah 1",
          after_summary["total_detection"] == before + 1,
          f"{before} -> {after_summary['total_detection']}")
    # Dicek berdasarkan ID (bukan posisi ke-0): timestamp detected_at
    # berpresisi detik, sehingga record yang dibuat pada detik yang
    # sama bisa seri urutannya.
    check("record baru muncul di /dashboard/recent",
          any(item["id"] == new_record_id for item in recent),
          f"record_id={new_record_id}")

    # Bersih-bersih file hasil test.
    for record in recent:
        for key in ("image_path", "annotated_image_path"):
            if record.get(key):
                Path(record[key]).unlink(missing_ok=True)
    shared_db.close()

    print(f"\n=== HASIL: {PASS} lolos, {FAIL} gagal ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    if "--live" in sys.argv:
        url = "http://localhost:8000"
        if "--url" in sys.argv:
            url = sys.argv[sys.argv.index("--url") + 1]
        sys.exit(run_live(url))
    sys.exit(run_tests())