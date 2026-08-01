# ESP32_API.md — Kontrak API untuk ESP32-CAM (v1)

> **Versi API: v1** — kontrak response di dokumen ini DIBEKUKAN.
> Perubahan yang merusak (mengubah/menghapus field) hanya akan dirilis
> sebagai v2 pada path baru (`/api/v2/esp32/...`); v1 dijaga
> kompatibel selamanya untuk firmware yang sudah beredar.

Dokumen referensi endpoint backend **Deteksi Tanaman Melon** yang
dipakai oleh (atau berkaitan dengan) perangkat ESP32-CAM AI Thinker.
Seluruh endpoint di dokumen ini **tidak memerlukan autentikasi**
(perangkat tidak dapat login).

Base URL: `http://<IP_SERVER>:8000`

---

## 1. POST `/api/esp32/detect` — kirim foto, terima hasil

Endpoint utama untuk firmware yang **mengirim (push)** foto ke server.
Menjalankan pipeline penuh: simpan → deteksi AI → anotasi → riwayat.

### Request

- Method: `POST`, body: `multipart/form-data`
- Field file: **`image`** (wajib persis nama ini)
- Header opsional: **`X-Device-Id`** — identitas perangkat (maks 64
  karakter, mis. `esp32-kebun-01`); tanpa header ini response memakai
  default `esp32-cam`. Berguna bila kelak ada lebih dari satu kamera.
- Ketentuan file:

| Ketentuan | Nilai |
|---|---|
| Ekstensi | `.jpg`, `.jpeg`, `.png` |
| Content-Type | `image/jpeg` atau `image/png` |
| Ukuran maksimal | 10 MB |
| Isi | JPEG/PNG valid (bukan sekadar berganti nama) |

- **Timeout klien yang disarankan: 15 detik** (inferensi + anotasi +
  tulis database; di hardware lambat bisa beberapa detik).

Contoh curl (menirukan ESP32):

```bash
curl -X POST http://192.168.1.10:8000/api/esp32/detect \
     -F "image=@foto.jpg;type=image/jpeg" \
     --max-time 15
```

### Response sukses — `200`, bentuk SELALU konsisten (7 field, v1)

```json
{
  "success": true,
  "label": "Tunas Air",
  "total_detection": 2,
  "record_id": "0b8c...-uuid",
  "annotated_image": "annotated/ab12cd_annotated.jpg",
  "device": "esp32-cam",
  "request_id": "a1b2c3d4e5f6"
}
```

- `label` — label deteksi ber-confidence tertinggi; `"No Detection"`
  bila tidak ada objek (field lain tetap ada, `total_detection: 0`).
- `annotated_image` — path relatif; gambar dapat diakses di
  `http://<IP_SERVER>:8000/<annotated_image>`.
- `device` — identitas perangkat (dari header `X-Device-Id`, default
  `esp32-cam`).
- `request_id` — 12 karakter heks unik per request; tercatat juga di
  log server, sehingga satu response dapat dilacak ke baris lognya
  saat debugging.
- Ketujuh field **selalu hadir** pada setiap response sukses — parser
  firmware cukup satu bentuk.

### Response error — `{"detail": "..."}`

| Status | Penyebab | Contoh detail |
|---|---|---|
| 400 | Ekstensi tidak didukung | `Ekstensi '.gif' tidak didukung. ...` |
| 400 | Content-Type tidak didukung | `Content-Type 'application/octet-stream' tidak didukung. ...` |
| 400 | File kosong | `Gambar kosong.` |
| 400 | Bukan gambar valid | `File tidak dapat dibaca sebagai gambar.` |
| 413 | Melebihi 10 MB | `Ukuran gambar 12.3 MB melebihi batas 10 MB.` |
| 404 | File hilang saat diproses | `File tidak ditemukan saat diproses.` |
| 500 | Kegagalan internal | `Terjadi kesalahan internal ...` |

Semua jalur gagal membersihkan file sementara di server; log
kegagalan menyertakan `request_id` yang sama.

### Kebijakan retry klien

- **Retry maksimal 3x dengan jeda 2 detik** untuk kegagalan jaringan
  (timeout/koneksi putus) dan status **5xx**.
- **Jangan retry** status **4xx** (400/413) — request-nya memang salah
  dan akan gagal lagi; perbaiki penyebabnya.
- Detail dan contoh kode: lihat `ESP32_SETUP.md` bagian
  "Strategi Retry".

### Parsing di firmware (Arduino, tanpa library JSON)

Karena bentuknya konsisten, pencarian substring sederhana cukup:

```cpp
bool ok      = payload.indexOf("\"success\":true") >= 0;
int  lblPos  = payload.indexOf("\"label\":\"") + 9;
String label = payload.substring(lblPos, payload.indexOf('"', lblPos));
```

---

## 2. Endpoint pendukung

### GET `/health`

Cek kesehatan server (dipakai firmware untuk memastikan server siap).

```json
{"status": "ok", "database": "connected", "model": "loaded",
 "version": "1.0.0"}
```

### GET `/api/esp32/status`

Kebalikan arah: **server** memeriksa apakah ESP32 terjangkau
(dipakai badge Online/Offline dashboard). Response:
`{"esp32": "online" | "offline" | "unconfigured", "esp32_url": ...}`.

### POST `/api/esp32/capture-detect`

Mode **pull**: server yang mengambil snapshot dari
`{ESP32_URL}/capture` lalu menjalankan pipeline — dipakai tombol
**Detect** pada panel Live Camera dashboard. Tanpa body. Error khas:
`503` (ESP32_URL belum diatur di `.env`), `502` (ESP32 tidak
terjangkau / snapshot tidak valid).

---

## 3. Dua pola integrasi

| Pola | Arah | Kapan dipakai |
|---|---|---|
| **Pull** (disarankan) | Server → `GET {ESP32_URL}/capture` | Firmware standar CameraWebServer, tanpa modifikasi; tombol Detect & stream live dashboard |
| **Push** | ESP32 → `POST /api/esp32/detect` | Firmware kustom yang mengirim berkala/berdasarkan trigger |

Keduanya bermuara ke pipeline dan riwayat yang sama — dashboard
(Total, Today, Recent History) ter-update otomatis lewat auto-refresh
maksimal 30 detik, dari sumber mana pun.

## 4. Simulator (tanpa hardware)

```bash
python test_esp32_api.py            # uji kontrak endpoint (16 cek)
python test_esp32_api.py --live     # kirim 1 snapshot ke server berjalan
python test_esp32_api.py --live --url http://192.168.1.10:8000
python test_esp32_stress.py           # stress: 20 upload beruntun
python test_esp32_stress.py --live    # stress terhadap server berjalan
```

Mode `--live` menirukan ESP32 sungguhan: kirim JPEG sintetis, cetak
response, lalu pantau dashboard ter-update sendiri.
