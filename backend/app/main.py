"""Entry point aplikasi FastAPI Deteksi Tanaman Melon."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.detection import router as detection_router
from app.api.esp32 import router as esp32_router
from app.api.history import router as history_router
from app.api.labels import router as labels_router
from app.api.monitor import router as monitor_router
from app.api.report import router as report_router
from app.api.prediction import router as prediction_router
from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Memuat model TFLite saat startup server.

    Dengan ini /health langsung melaporkan model "loaded" sejak awal,
    /system/info langsung menampilkan input size, dan request deteksi
    pertama tidak menanggung waktu load model. Jika model gagal dimuat,
    server tetap berjalan (endpoint deteksi akan mengembalikan 503)
    agar /health tetap bisa melaporkan kondisi sistem.
    """
    from app.ai.tflite_engine import TFLiteEngine

    logger.info("Startup: aplikasi %s dimulai.", settings.APP_NAME)
    try:
        TFLiteEngine().load_model()
        logger.info("Startup: model TFLite berhasil dimuat.")
    except (FileNotFoundError, RuntimeError) as exc:
        logger.error("Startup: model TFLite gagal dimuat: %s", exc)

    yield

    logger.info("Shutdown: aplikasi %s dihentikan.", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="API deteksi pemangkasan tanaman melon berbasis "
    "MobileNetV2 FOMO dan ESP32-CAM.",
    lifespan=lifespan,
)

# CORS: izinkan ESP32, web dashboard, dan browser mengakses API.
# allow_origins=["*"] hanya untuk development; batasi ke domain
# frontend saat production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrasi router. esp32_router didaftarkan PERTAMA agar endpoint
# /health versi lengkap (status, database, model, version) selalu
# diprioritaskan bila ada route lama dengan path sama.
app.include_router(esp32_router)
app.include_router(prediction_router)
app.include_router(detection_router)
app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(report_router)
app.include_router(monitor_router)
app.include_router(labels_router)

# Static file serving: agar frontend dapat menampilkan gambar asli dan
# gambar anotasi hasil deteksi. Folder dibuat bila belum ada.
Path("uploads").mkdir(parents=True, exist_ok=True)
Path("annotated").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/annotated", StaticFiles(directory="annotated"), name="annotated")