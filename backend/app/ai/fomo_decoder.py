"""FOMO Decoder: mengubah output model FOMO menjadi daftar objek.

Sejak penambahan Connected Component Analysis, decoder tidak lagi
memperlakukan satu grid cell sebagai satu objek. Cell bertetangga
(8-connectivity) yang berlabel sama dan lolos threshold digabung
menjadi SATU objek beserta bounding rectangle pada ruang grid.

Pipeline:
    tensor -> cell kandidat -> connected component -> objek

Decoder tetap murni decoding (SRP): tidak menggambar apa pun dan tidak
menyentuh PredictionService, AnnotationService, maupun API.
"""

import logging
from collections import deque
from typing import Final, NamedTuple

import numpy as np

from app.ai.labels import get_label

logger = logging.getLogger(__name__)

# Toleransi untuk mendeteksi apakah nilai satu cell sudah berupa
# distribusi probabilitas (jumlah ~1) atau masih logits.
_PROBABILITY_SUM_TOLERANCE: float = 0.05

# 8-connectivity: atas, bawah, kiri, kanan, dan 4 diagonal.
_NEIGHBOR_OFFSETS: Final[tuple[tuple[int, int], ...]] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)


class _Cell(NamedTuple):
    """Satu grid cell kandidat (lolos background dan threshold).

    Attributes:
        grid_x: Kolom cell pada grid.
        grid_y: Baris cell pada grid.
        class_id: Indeks channel pada output model.
        label: Nama label hasil pemetaan.
        confidence: Probabilitas class terpilih pada cell ini.
    """

    grid_x: int
    grid_y: int
    class_id: int
    label: str
    confidence: float


class FOMODecoder:
    """Decoder output FOMO (grid heatmap) menjadi list objek.

    Attributes:
        threshold: Ambang confidence minimum agar cell dianggap valid.
        background_class_index: Indeks channel background yang
            diabaikan. Default -1 (class terakhir); model Edge Impulse
            menaruh background di indeks 0 — untuk model asli gunakan
            FOMODecoder(background_class_index=0).
    """

    def __init__(
        self,
        threshold: float = 0.5,
        background_class_index: int = -1,
    ) -> None:
        """Menginisialisasi decoder.

        Args:
            threshold: Ambang confidence (default 0.5).
            background_class_index: Indeks class background (default -1,
                yaitu class terakhir).

        Raises:
            ValueError: Jika threshold di luar rentang 0..1.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                f"threshold harus di rentang 0..1, diterima: {threshold}"
            )
        self.threshold: float = threshold
        self.background_class_index: int = background_class_index

    # ------------------------------------------------------------------
    # Probabilitas per cell (tidak berubah)
    # ------------------------------------------------------------------

    @staticmethod
    def _softmax(values: np.ndarray) -> np.ndarray:
        """Menghitung softmax yang stabil secara numerik.

        Args:
            values: Vektor logits satu grid cell.

        Returns:
            np.ndarray: Probabilitas softmax, jumlah = 1.
        """
        shifted = values - np.max(values)
        exp = np.exp(shifted)
        return exp / np.sum(exp)

    @classmethod
    def _to_probabilities(cls, values: np.ndarray) -> np.ndarray:
        """Mengembalikan distribusi probabilitas untuk satu cell.

        Jika nilai sudah berupa probabilitas (seluruhnya di rentang
        0..1 dan berjumlah ~1, seperti output FOMO yang sudah
        di-dequantize), nilai dipakai apa adanya — menerapkan softmax
        kedua pada probabilitas akan meratakan distribusi dan merusak
        confidence. Jika nilai masih logits, softmax diterapkan.

        Args:
            values: Vektor nilai satu grid cell.

        Returns:
            np.ndarray: Distribusi probabilitas.
        """
        total = float(np.sum(values))
        if (
            float(values.min()) >= 0.0
            and float(values.max()) <= 1.0
            and abs(total - 1.0) <= _PROBABILITY_SUM_TOLERANCE
        ):
            return values
        return cls._softmax(values)

    # ------------------------------------------------------------------
    # Tahap 1: tensor -> cell kandidat
    # ------------------------------------------------------------------

    def _extract_candidate_cells(
        self, grid: np.ndarray, background_index: int
    ) -> dict[tuple[int, int], _Cell]:
        """Menyaring grid menjadi cell kandidat objek.

        Satu cell menjadi kandidat bila class hasil argmax bukan
        background DAN confidence-nya >= threshold (aturan gabung
        nomor 3 dipenuhi di tahap ini).

        Args:
            grid: Tensor (H, W, C) tanpa batch dimension.
            background_index: Indeks channel background (sudah positif).

        Returns:
            dict: Peta (grid_y, grid_x) -> _Cell untuk cell kandidat.
        """
        grid_h, grid_w, _ = grid.shape
        candidates: dict[tuple[int, int], _Cell] = {}

        for grid_y in range(grid_h):
            for grid_x in range(grid_w):
                cell_values: np.ndarray = grid[grid_y, grid_x]
                class_id: int = int(np.argmax(cell_values))

                if class_id == background_index:
                    continue

                probabilities: np.ndarray = self._to_probabilities(
                    cell_values
                )
                confidence: float = float(probabilities[class_id])
                if confidence < self.threshold:
                    continue

                # Indeks label = urutan class di antara class
                # non-background, sehingga mapping LABELS (0..4) tetap
                # benar apa pun posisi background.
                label_id: int = (
                    class_id - 1 if class_id > background_index else class_id
                )
                candidates[(grid_y, grid_x)] = _Cell(
                    grid_x=grid_x,
                    grid_y=grid_y,
                    class_id=class_id,
                    label=get_label(label_id),
                    confidence=confidence,
                )

        return candidates

    # ------------------------------------------------------------------
    # Tahap 2: cell kandidat -> cluster (connected component)
    # ------------------------------------------------------------------

    @staticmethod
    def _expand_cluster(
        start: tuple[int, int],
        cells: dict[tuple[int, int], _Cell],
        visited: set[tuple[int, int]],
    ) -> list[_Cell]:
        """Menelusuri satu cluster dari cell awal memakai BFS.

        Penelusuran memakai 8-connectivity dan hanya menerima tetangga
        dengan class_id sama (aturan gabung nomor 1 dan 2). BFS dipilih
        (iteratif, bukan rekursif) agar aman untuk grid besar tanpa
        risiko RecursionError.

        Args:
            start: Koordinat (grid_y, grid_x) awal penelusuran.
            cells: Peta seluruh cell kandidat.
            visited: Himpunan koordinat yang sudah dikunjungi;
                diperbarui in-place.

        Returns:
            list[_Cell]: Seluruh cell anggota cluster.
        """
        target_class_id: int = cells[start].class_id
        queue: deque[tuple[int, int]] = deque([start])
        visited.add(start)
        cluster: list[_Cell] = []

        while queue:
            current_y, current_x = queue.popleft()
            cluster.append(cells[(current_y, current_x)])

            for offset_y, offset_x in _NEIGHBOR_OFFSETS:
                neighbor = (current_y + offset_y, current_x + offset_x)
                if neighbor in visited:
                    continue
                neighbor_cell = cells.get(neighbor)
                if (
                    neighbor_cell is not None
                    and neighbor_cell.class_id == target_class_id
                ):
                    visited.add(neighbor)
                    queue.append(neighbor)

        return cluster

    def _find_connected_components(
        self, cells: dict[tuple[int, int], _Cell]
    ) -> list[list[_Cell]]:
        """Mengelompokkan cell kandidat menjadi cluster objek.

        Args:
            cells: Peta seluruh cell kandidat.

        Returns:
            list[list[_Cell]]: Daftar cluster; satu cluster = satu objek.
        """
        visited: set[tuple[int, int]] = set()
        clusters: list[list[_Cell]] = []

        # Iterasi terurut (baris lalu kolom) agar hasil deterministik.
        for coordinate in sorted(cells):
            if coordinate in visited:
                continue
            clusters.append(self._expand_cluster(coordinate, cells, visited))

        return clusters

    # ------------------------------------------------------------------
    # Tahap 3: cluster -> satu deteksi objek
    # ------------------------------------------------------------------

    @staticmethod
    def _build_detection(cluster: list[_Cell]) -> dict:
        """Merangkum satu cluster menjadi satu dict deteksi.

        Confidence objek = confidence TERTINGGI di antara cell anggota
        (bukan rata-rata). Field grid_x/grid_y lama dipertahankan dan
        diisi koordinat cell ber-confidence tertinggi (peak cell),
        sehingga tetap backward compatible sekaligus konsisten dengan
        nilai confidence yang dilaporkan.

        Args:
            cluster: Daftar cell anggota satu objek (tidak kosong).

        Returns:
            dict: Deteksi objek beserta bounding rectangle pada grid.
        """
        peak_cell: _Cell = max(cluster, key=lambda cell: cell.confidence)
        xs: list[int] = [cell.grid_x for cell in cluster]
        ys: list[int] = [cell.grid_y for cell in cluster]

        return {
            "class_id": peak_cell.class_id,
            "label": peak_cell.label,
            "confidence": peak_cell.confidence,
            # Backward compatible: koordinat cell terkuat pada objek ini.
            "grid_x": peak_cell.grid_x,
            "grid_y": peak_cell.grid_y,
            # Bounding rectangle objek pada ruang grid (inklusif).
            "grid_x_min": min(xs),
            "grid_y_min": min(ys),
            "grid_x_max": max(xs),
            "grid_y_max": max(ys),
            "merged": len(cluster) > 1,
            "cell_count": len(cluster),
        }

    # ------------------------------------------------------------------
    # API publik
    # ------------------------------------------------------------------

    def decode(self, raw_output: np.ndarray) -> list[dict]:
        """Mengubah tensor FOMO menjadi daftar objek terdeteksi.

        Algoritma: hilangkan batch dimension -> saring cell kandidat
        (bukan background, confidence >= threshold) -> gabungkan cell
        bertetangga berlabel sama dengan connected component analysis
        (8-connectivity, BFS) -> rangkum tiap cluster menjadi satu objek
        beserta bounding rectangle pada ruang grid.

        Catatan: tensor INT8 quantized harus di-dequantize terlebih
        dahulu sebelum masuk ke decoder (dilakukan DetectionService).

        Args:
            raw_output: Tensor shape (1, grid_h, grid_w, num_classes),
                misal (1, 12, 12, 6), float32.

        Returns:
            list[dict]: Setiap objek berformat
                {"class_id": int, "label": str, "confidence": float,
                 "grid_x": int, "grid_y": int,
                 "grid_x_min": int, "grid_y_min": int,
                 "grid_x_max": int, "grid_y_max": int,
                 "merged": bool, "cell_count": int}.
                Terurut menurun berdasarkan confidence.

        Raises:
            TypeError: Jika input bukan numpy.ndarray.
            ValueError: Jika shape tensor tidak sesuai format FOMO.
        """
        if not isinstance(raw_output, np.ndarray):
            raise TypeError(
                f"raw_output harus numpy.ndarray, diterima: "
                f"{type(raw_output).__name__}"
            )
        if raw_output.ndim != 4 or raw_output.shape[0] != 1:
            raise ValueError(
                f"Shape tidak sesuai format FOMO (1, H, W, C), "
                f"diterima: {raw_output.shape}"
            )

        # Hilangkan batch dimension: (1, H, W, C) -> (H, W, C).
        grid: np.ndarray = raw_output[0].astype(np.float32)
        grid_h, grid_w, num_classes = grid.shape

        # Normalisasi indeks background (dukung indeks negatif).
        background_index: int = self.background_class_index % num_classes

        cells = self._extract_candidate_cells(grid, background_index)
        clusters = self._find_connected_components(cells)
        detections: list[dict] = [
            self._build_detection(cluster) for cluster in clusters
        ]
        detections.sort(key=lambda item: item["confidence"], reverse=True)

        logger.info(
            "Decode selesai: %d objek dari %d cell aktif pada grid "
            "%dx%d (threshold %.2f).",
            len(detections),
            len(cells),
            grid_h,
            grid_w,
            self.threshold,
        )
        return detections