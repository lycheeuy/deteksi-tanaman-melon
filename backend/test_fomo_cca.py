"""Uji Connected Component Analysis pada FOMODecoder.

Jalankan dari folder backend/ (venv aktif):
    python test_fomo_cca.py

Tidak butuh model, database, atau TensorFlow — hanya numpy + decoder.
Grid dibuat manual sehingga hasil yang benar bisa dihitung tangan.
"""

import numpy as np

from app.ai.fomo_decoder import FOMODecoder

GRID_H, GRID_W, NUM_CLASSES = 12, 12, 6
BACKGROUND_INDEX = 0          # model Edge Impulse: background di index 0

PASS = FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    ok = "LOLOS" if condition else "GAGAL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{ok}] {name}" + (f" | {detail}" if detail else ""))


def empty_grid() -> np.ndarray:
    """Grid berisi background penuh (probabilitas, jumlah tiap cell = 1)."""
    grid = np.zeros((1, GRID_H, GRID_W, NUM_CLASSES), dtype=np.float32)
    grid[0, :, :, BACKGROUND_INDEX] = 1.0
    return grid


def set_cell(grid, y: int, x: int, class_id: int, conf: float) -> None:
    """Mengaktifkan satu cell: class_id dengan confidence tertentu."""
    grid[0, y, x, :] = 0.0
    grid[0, y, x, class_id] = conf
    grid[0, y, x, BACKGROUND_INDEX] = 1.0 - conf


decoder = FOMODecoder(threshold=0.5, background_class_index=BACKGROUND_INDEX)

# ---------- [1] Satu blok 2x2 = SATU objek ----------
print("\n[1] Blok 2x2 berlabel sama")
g = empty_grid()
for y, x, c in [(4, 5, 0.70), (4, 6, 0.84), (5, 5, 0.66), (5, 6, 0.79)]:
    set_cell(g, y, x, 3, c)          # class 3 -> label_id 2
d = decoder.decode(g)
check("menghasilkan 1 objek (bukan 4)", len(d) == 1, f"dapat {len(d)}")
if d:
    o = d[0]
    check("cell_count = 4", o["cell_count"] == 4)
    check("merged = True", o["merged"] is True)
    check("confidence = MAX (0.84), bukan rata-rata",
          abs(o["confidence"] - 0.84) < 1e-6, f"{o['confidence']:.4f}")
    check("bbox grid benar (x 5-6, y 4-5)",
          (o["grid_x_min"], o["grid_x_max"],
           o["grid_y_min"], o["grid_y_max"]) == (5, 6, 4, 5))
    check("grid_x/grid_y = peak cell (6,4)",
          (o["grid_x"], o["grid_y"]) == (6, 4))
    check("field lama tetap ada (backward compatible)",
          all(k in o for k in ("class_id", "label", "confidence",
                               "grid_x", "grid_y")))

# ---------- [2] Dua blok terpisah = DUA objek ----------
print("\n[2] Dua blok terpisah jauh")
g = empty_grid()
set_cell(g, 1, 1, 3, 0.80); set_cell(g, 1, 2, 3, 0.75)
set_cell(g, 9, 9, 3, 0.90); set_cell(g, 9, 10, 3, 0.60)
d = decoder.decode(g)
check("menghasilkan 2 objek", len(d) == 2, f"dapat {len(d)}")
check("terurut confidence menurun",
      len(d) == 2 and d[0]["confidence"] >= d[1]["confidence"])

# ---------- [3] Tetangga DIAGONAL ikut tergabung (8-connectivity) ----
print("\n[3] Dua cell diagonal")
g = empty_grid()
set_cell(g, 3, 3, 3, 0.70); set_cell(g, 4, 4, 3, 0.80)
d = decoder.decode(g)
check("diagonal dianggap satu objek", len(d) == 1, f"dapat {len(d)}")
check("cell_count = 2", d and d[0]["cell_count"] == 2)

# ---------- [4] Bertetangga tapi LABEL BERBEDA = tidak digabung -----
print("\n[4] Dua cell bertetangga, label berbeda")
g = empty_grid()
set_cell(g, 6, 6, 3, 0.80)      # Buah Siap Panen
set_cell(g, 6, 7, 5, 0.75)      # Tunas Air
d = decoder.decode(g)
check("tetap 2 objek terpisah", len(d) == 2, f"dapat {len(d)}")
check("label berbeda",
      len(d) == 2 and d[0]["label"] != d[1]["label"])

# ---------- [5] Cell di bawah threshold diabaikan ----------
print("\n[5] Threshold")
g = empty_grid()
set_cell(g, 2, 2, 3, 0.80)      # lolos
set_cell(g, 2, 3, 3, 0.30)      # di bawah threshold -> diabaikan
d = decoder.decode(g)
check("hanya cell kuat yang dihitung",
      len(d) == 1 and d[0]["cell_count"] == 1,
      f"objek={len(d)}")
check("merged = False untuk objek 1 cell",
      d and d[0]["merged"] is False)

# ---------- [6] Grid kosong ----------
print("\n[6] Grid tanpa objek")
check("0 objek", len(decoder.decode(empty_grid())) == 0)

# ---------- [7] Bentuk L (7 cell) ----------
print("\n[7] Bentuk tidak beraturan (L)")
g = empty_grid()
for y, x in [(7, 2), (8, 2), (9, 2), (9, 3), (9, 4), (8, 4), (7, 4)]:
    set_cell(g, y, x, 2, 0.72)
d = decoder.decode(g)
check("tetap 1 objek", len(d) == 1, f"dapat {len(d)}")
check("cell_count = 7", d and d[0]["cell_count"] == 7)
check("bbox menutupi seluruh bentuk L",
      d and (d[0]["grid_x_min"], d[0]["grid_x_max"],
             d[0]["grid_y_min"], d[0]["grid_y_max"]) == (2, 4, 7, 9))

print(f"\n=== HASIL: {PASS} lolos, {FAIL} gagal ===")
raise SystemExit(0 if FAIL == 0 else 1)