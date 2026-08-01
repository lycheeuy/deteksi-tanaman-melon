# Panduan Pengujian API — Deteksi Tanaman Melon (Phase 21)

## 1. Cara Menjalankan Server

Pastikan dependency terpasang di virtual environment:

```bash
pip install fastapi uvicorn python-multipart
```

> `python-multipart` wajib untuk menerima upload `multipart/form-data`.

Pastikan `.env` berisi `MODEL_PATH` yang benar, lalu jalankan dari
folder `backend/`:

```bash
uvicorn app.main:app --reload
```

Server berjalan di `http://127.0.0.1:8000`. Flag `--reload` otomatis
me-restart server saat kode berubah (hanya untuk development).

## 2. Cara Membuka Swagger

Buka browser dan akses:

```
http://127.0.0.1:8000/docs
```

Swagger UI menampilkan seluruh endpoint beserta form pengujian
interaktif. Alternatif dokumentasi ReDoc tersedia di
`http://127.0.0.1:8000/redoc`.

## 3. Cara Menguji Endpoint Menggunakan Swagger

### GET /

1. Klik baris **GET /**.
2. Klik **Try it out** lalu **Execute**.
3. Response yang diharapkan (kode 200):

```json
{
  "message": "Deteksi Tanaman Melon API",
  "status": "running"
}
```

### GET /health

1. Klik baris **GET /health**.
2. Klik **Try it out** lalu **Execute**.
3. Response yang diharapkan (kode 200):

```json
{
  "status": "healthy"
}
```

### POST /predict

1. Klik baris **POST /predict**.
2. Klik **Try it out**.
3. Pada field **image**, klik **Choose File** dan pilih gambar
   berekstensi `.jpg`, `.jpeg`, atau `.png` (misalnya foto tanaman
   melon dari ESP32-CAM).
4. Klik **Execute**.
5. Response yang diharapkan (kode 200):

```json
{
  "success": true,
  "input_shape": [1, 96, 96, 3],
  "output_shape": [[1, 12, 12, 6]],
  "raw_output_shape": [[1, 12, 12, 6]]
}
```

> Nilai shape menyesuaikan model `.tflite` Anda. Tensor mentah sengaja
> tidak dikembalikan.

### Pengujian Kasus Gagal

- Upload file non-gambar (mis. `.txt` atau `.pdf`) → response **400**
  dengan pesan ekstensi tidak didukung.
- Upload file `.jpg` yang isinya rusak/bukan gambar → response **400**
  "File tidak dapat dibaca sebagai gambar".
- Jika `MODEL_PATH` salah, endpoint `/predict` mengembalikan **503**
  "Model AI tidak tersedia".

### Verifikasi Kebersihan File Temporary

Setelah beberapa kali menguji `/predict`, periksa folder
`uploads/temp/` — folder harus kosong karena file selalu dihapus
setelah inferensi (berhasil maupun gagal).
