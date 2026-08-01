# ESP32_SETUP.md — Panduan Setup ESP32-CAM AI Thinker

Panduan menyiapkan perangkat ESP32-CAM AI Thinker untuk sistem
**Deteksi Tanaman Melon** — dari flashing firmware sampai tersambung
ke dashboard. Ditulis untuk pola **pull** (server mengambil snapshot
dari ESP32; firmware standar tanpa modifikasi).

---

## 1. Perangkat yang Dibutuhkan

| Item | Catatan |
|---|---|
| ESP32-CAM AI Thinker | Modul dengan kamera OV2640 |
| USB-to-TTL (FTDI FT232RL / CP2102) | ESP32-CAM tidak punya port USB |
| Kabel jumper female-female | Minimal 5 utas |
| Catu daya 5V yang kuat | Kamera + WiFi boros; port USB laptop sering kurang — siapkan adaptor 5V ≥1A |

Wiring flashing (FTDI ↔ ESP32-CAM):

```
FTDI 5V   -> 5V          FTDI TX -> U0R (RX)
FTDI GND  -> GND         FTDI RX -> U0T (TX)
GPIO0     -> GND  (HANYA saat flashing; lepas untuk mode normal)
```

## 2. Arduino IDE

1. Install Arduino IDE (2.x).
2. `File → Preferences → Additional Boards Manager URLs`, tambahkan:
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. `Tools → Board → Boards Manager` → cari **esp32** (Espressif) →
   Install.
4. Pilih board: `Tools → Board → ESP32 Arduino → AI Thinker ESP32-CAM`.

## 3. Firmware CameraWebServer (bawaan, tanpa modifikasi)

1. `File → Examples → ESP32 → Camera → CameraWebServer`.
2. Di bagian atas sketch, pastikan model kamera:

   ```cpp
   // #define CAMERA_MODEL_WROVER_KIT
   #define CAMERA_MODEL_AI_THINKER   // aktifkan baris ini
   ```

3. Isi kredensial WiFi (**harus jaringan yang sama** dengan
   laptop/server backend):

   ```cpp
   const char* ssid     = "NamaWiFiAnda";
   const char* password = "PasswordWiFi";
   ```

4. Flashing: hubungkan `GPIO0 → GND`, colok FTDI, tekan tombol
   **RST** kecil di modul, lalu klik **Upload**. Jika gagal
   "Failed to connect", tekan RST lagi tepat saat "Connecting...".
5. Setelah "Done uploading": **lepas GPIO0 dari GND**, tekan RST.
6. Buka `Tools → Serial Monitor` (115200 baud) — catat baris:

   ```
   Camera Ready! Use 'http://192.168.1.50' to connect
   ```

   IP itulah alamat ESP32 Anda.

## 4. Uji Perangkat (browser)

| URL | Harus tampil |
|---|---|
| `http://<IP_ESP32>/` | Halaman kontrol kamera bawaan |
| `http://<IP_ESP32>/capture` | Satu foto JPEG (snapshot) |
| `http://<IP_ESP32>:81/stream` | Video MJPEG live |

Ketiganya wajib jalan sebelum lanjut. Perhatikan: **snapshot di port
80, stream di port 81** — dua hal berbeda.

## 5. Sambungkan ke Sistem

**Backend** — `backend/.env`:

```ini
ESP32_URL=http://192.168.1.50        # TANPA :81, TANPA /capture
```

**Frontend** — `frontend/.env.local`:

```ini
NEXT_PUBLIC_ESP32_STREAM_URL=http://192.168.1.50:81/stream
```

Restart uvicorn dan `npm run dev`, lalu buka dashboard:

1. Badge panel Live Camera → **ESP32 Online**, stream tampil.
2. Klik **Detect** → snapshot diambil server → hasil (gambar asli +
   anotasi + label) muncul, Total/Today/Recent History bertambah.
3. Halaman History mencatat record baru.

## 6. Uji Tanpa Hardware (simulator)

Belum pegang perangkat? Simulator menirukan ESP32 dari PC:

```bash
cd backend
python test_esp32_api.py            # 16 pengecekan kontrak endpoint
python test_esp32_api.py --live     # kirim snapshot sintetis ke server
```

Mode `--live` membuat record sungguhan — dashboard ter-update
otomatis persis seperti dari perangkat asli.

## 7. Troubleshooting

| Gejala | Penyebab umum | Solusi |
|---|---|---|
| "Brownout detector was triggered" di Serial Monitor | Catu daya lemah | Pakai adaptor 5V ≥1A, kabel pendek |
| Upload gagal "Failed to connect" | GPIO0 tidak ke GND / timing RST | Cek jumper, tekan RST saat "Connecting..." |
| Stream jalan tapi Detect 502 | `ESP32_URL` salah port | Isi tanpa `:81` (snapshot di port 80) |
| Badge Offline padahal ESP32 nyala | Beda subnet / firewall laptop | Pastikan satu WiFi; ping IP ESP32 |
| Stream sering putus | ESP32 kehabisan koneksi (stream + snapshot bersamaan) | Wajar; panel punya auto-reconnect 5/10/15 dtk — tutup tab lain yang membuka stream |
| Gambar gelap/hijau | Kamera belum fokus / pita kabel kamera kendor | Buka kunci konektor, pasang ulang pita kamera |

## 8. Strategi Retry (firmware / klien)

Jaringan WiFi kebun tidak selalu stabil. Ketentuan retry yang
disarankan (dan dipakai sebagai acuan sistem):

- **Maksimal 3 percobaan, jeda tetap 2 detik** antar percobaan.
- Retry hanya untuk **kegagalan jaringan** (timeout, koneksi putus)
  dan **status 5xx**.
- **Jangan** retry status **4xx** (400 format salah, 413 kebesaran) —
  penyebabnya di sisi pengirim; mengulang hanya membebani server.
- Timeout per percobaan: 15 detik (lihat ESP32_API.md).

Contoh pola pada firmware Arduino:

```cpp
const int MAX_RETRY   = 3;
const int RETRY_DELAY = 2000;  // ms

int httpCode = -1;
for (int attempt = 1; attempt <= MAX_RETRY; attempt++) {
  httpCode = kirimFoto();               // POST /api/esp32/detect
  if (httpCode == 200) break;           // sukses
  if (httpCode >= 400 && httpCode < 500) break;  // 4xx: jangan diulang
  Serial.printf("Percobaan %d gagal (%d), coba lagi 2 dtk...\n",
                attempt, httpCode);
  delay(RETRY_DELAY);
}
```

Catatan: mode pull (server mengambil `/capture`) tidak membutuhkan
logika ini di perangkat — kegagalan cukup ditangani tombol
Retry/auto-reconnect di dashboard.

## 9. Catatan Keamanan

Firmware CameraWebServer tidak punya autentikasi — siapa pun di
jaringan yang sama dapat melihat stream. Untuk produksi: tempatkan
ESP32 dan server pada VLAN/jaringan khusus, dan jangan ekspos port
ESP32 ke internet. Endpoint backend `/api/esp32/*` memang tidak
ber-autentikasi (perangkat tidak bisa login) — batasi akses pada
level jaringan/firewall bila server dipublikasikan.
