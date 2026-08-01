"""Single source of truth untuk nama label deteksi FOMO.

SELURUH sistem mengambil nama label dari sini (bounding box, dashboard,
history, detail, API response, database, export) melalui get_label().
Untuk mengganti nama tampilan label, cukup ubah nilai pada LABELS —
JANGAN mengubah urutan/angka class_id, karena itu terikat pada model.

Nama label ditulis PERSIS seperti pada model Edge Impulse
(model-parameters/model_variables.h -> ei_classifier_inferencing_categories):
    0 -> Tunas Air
    1 -> buah siap
    2 -> buah tidak
    3 -> daun siap
    4 -> daun tidak
"""

import logging
from typing import Final

logger = logging.getLogger(__name__)

UNKNOWN_LABEL: Final[str] = "Unknown"

LABELS: Final[dict[int, str]] = {
    0: "Tunas Air",
    1: "buah siap",
    2: "buah tidak",
    3: "daun siap",
    4: "daun tidak",
}


def get_label(class_id: int) -> str:
    """Mengembalikan nama label untuk sebuah class_id.

    Args:
        class_id: Indeks class hasil decoder FOMO.

    Returns:
        str: Nama label jika ditemukan, "Unknown" jika tidak ada.
    """
    label = LABELS.get(class_id)
    if label is None:
        logger.warning(
            "class_id %s tidak ditemukan pada LABELS, "
            "mengembalikan '%s'.",
            class_id,
            UNKNOWN_LABEL,
        )
        return UNKNOWN_LABEL
    return label


def all_labels() -> list[str]:
    """Mengembalikan seluruh nama label urut berdasarkan class_id.

    Dipakai endpoint /labels agar frontend memperoleh daftar label dari
    satu sumber yang sama (tanpa hardcode ganda di frontend).

    Returns:
        list[str]: Nama label terurut menaik menurut class_id.
    """
    return [LABELS[class_id] for class_id in sorted(LABELS)]