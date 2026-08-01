"""Endpoint publik daftar label — sumber tunggal untuk frontend.

Frontend memanggil GET /labels untuk mengisi dropdown filter dan
komponen lain, sehingga tidak ada salinan hardcode nama label di sisi
frontend. Nama label berasal dari app/ai/labels.py (single source of
truth); mengubah label cukup di satu tempat.
"""

from fastapi import APIRouter

from app.ai.labels import all_labels

router = APIRouter()


@router.get("/labels")
def get_labels() -> dict[str, list[str]]:
    """Mengembalikan seluruh nama label deteksi urut menurut class_id.

    Returns:
        dict: {"labels": ["Tunas Air", "Buah Siap", ...]}
    """
    return {"labels": all_labels()}