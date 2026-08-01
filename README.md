# 🍈 MelonVision AI

> **AI-Based Melon Plant Detection System using ESP32-CAM, TensorFlow Lite, FastAPI, Next.js, and PostgreSQL**

MelonVision AI adalah sistem berbasis Artificial Intelligence yang dirancang untuk membantu proses pemantauan tanaman melon secara real-time menggunakan **ESP32-CAM**. Sistem mampu mendeteksi beberapa objek penting pada tanaman melon menggunakan model **TensorFlow Lite (FOMO)** dan menampilkan hasil deteksi melalui dashboard berbasis web.

---

# 📌 Features

* 📷 Live Camera Streaming dari ESP32-CAM
* 🤖 AI Object Detection menggunakan TensorFlow Lite
* 📦 Bounding Box Detection
* 🏷️ Multi-Class Detection

  * Tunas Air
  * buah siap
  * buah tidak
  * daun siap
  * daun tidak
     
* 📊 Dashboard Monitoring
* 📜 Detection History
* 📈 Detection Statistics
* 💾 PostgreSQL Database
* 📤 REST API dengan FastAPI
* 🌐 Web Interface menggunakan Next.js
* ☁️ VPS Deployment Support

---

# 🏗️ System Architecture

```text
ESP32-CAM
     │
     ▼
Capture Image
     │
     ▼
FastAPI Backend
     │
     ├── AI Detection (TensorFlow Lite)
     ├── Database Service
     └── REST API
     │
     ▼
PostgreSQL
     │
     ▼
Next.js Dashboard
     │
     ▼
User
```

---

# 🛠️ Technology Stack

## Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS

## Backend

* FastAPI
* SQLAlchemy
* Uvicorn
* Pydantic

## Artificial Intelligence

* TensorFlow Lite
* MobileNetV2 FOMO

## Database

* PostgreSQL

## Hardware

* ESP32-CAM AI Thinker

## Deployment

* Ubuntu VPS
* Nginx
* Systemd

---

# 📂 Project Structure

```text
melon-ai/

├── backend/
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── database/
│   │   ├── models/
│   │   ├── services/
│   │   └── utils/
│   │
│   ├── uploads/
│   ├── annotated/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── public/
│
└── docs/
```

---

# 🚀 Main Features

## Live Streaming

Dashboard dapat menampilkan live stream dari ESP32-CAM melalui backend proxy sehingga tidak mengalami masalah CORS ketika diakses dari browser.

---

## AI Detection

Backend mengambil gambar dari ESP32-CAM kemudian menjalankan inferensi menggunakan TensorFlow Lite.

Output berupa:

* Label
* Confidence Score
* Bounding Box
* Detection Time

---

## Detection History

Setiap hasil deteksi otomatis disimpan ke PostgreSQL sehingga dapat:

* Dilihat kembali
* Dicari
* Difilter
* Diekspor

---

## Dashboard

Dashboard menyediakan informasi:

* Total Detection
* Today's Detection
* Latest Detection
* AI Status
* Backend Status
* ESP32 Status

---

# 📡 REST API

Beberapa endpoint utama:

| Method | Endpoint                    | Description              |
| ------ | --------------------------- | ------------------------ |
| GET    | `/health`                   | Backend Health Check     |
| GET    | `/dashboard/summary`        | Dashboard Summary        |
| GET    | `/dashboard/recent`         | Latest Detection         |
| POST   | `/api/esp32/capture-detect` | Capture dan AI Detection |
| GET    | `/api/esp32/stream`         | Live Stream Proxy        |
| GET    | `/history`                  | Detection History        |

---

# ⚙️ Environment Variables

Contoh konfigurasi `.env`

```env
DATABASE_URL=postgresql://user:password@localhost/melon_ai

ESP32_URL=http://192.168.1.100

MODEL_PATH=app/ai/model.tflite

UPLOAD_DIR=uploads
```

---

# ▶️ Running Project

## Backend

```bash
cd backend

source .venv/bin/activate

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# 🔄 Deployment

Backend berjalan menggunakan:

* FastAPI
* Uvicorn
* Systemd

Frontend berjalan menggunakan:

* Next.js
* PM2

Server menggunakan:

* Ubuntu VPS
* Nginx Reverse Proxy

---

# 🤖 AI Model

Model yang digunakan:

* TensorFlow Lite
* MobileNetV2 FOMO

Object yang dideteksi:

 * Tunas Air
 * buah siap
 * buah tidak
 * daun siap
 * daun tidak

---

# 🔄 Mengganti Model AI

Untuk mengganti model:

1. Salin file `.tflite` baru ke folder model.
2. Perbarui konfigurasi `MODEL_PATH` atau ganti nama model sesuai kebutuhan.
3. Restart backend.
4. Lakukan pengujian untuk memastikan label, confidence threshold, dan ukuran input sesuai dengan model baru.

---

# 📶 Mengganti WiFi ESP32

Jika ESP32 berpindah jaringan:

1. Ubah SSID dan Password pada sketch Arduino.
2. Upload ulang firmware ke ESP32.
3. Catat alamat IP baru yang diperoleh ESP32.
4. Perbarui nilai `ESP32_URL` pada file `.env` backend.
5. Restart backend agar konfigurasi baru diterapkan.

---

# 📖 Documentation

Dokumentasi lebih lengkap tersedia pada folder:

```text
docs/

INSTALLATION.md
DEPLOYMENT.md
ESP32_SETUP.md
AI_MODEL_GUIDE.md
API_REFERENCE.md
TROUBLESHOOTING.md
```

---

# 📌 Roadmap

* Multiple AI Model Support
* Model Manager Dashboard
* Auto Model Switching
* User Authentication
* MQTT Integration
* Docker Deployment
* Docker Compose
* OTA ESP32 Update
* Export PDF Report
* Notification System

---

# 👨‍💻 Developer

**Nashiruddin Alif Alvareezi**

* AI Engineer
* Machine Learning Enthusiast
* Full Stack Developer
---

# 📄 License

This project is developed for educational and research purposes.

Copyright © 2026 Nashiruddin Alif Alvareezi.
