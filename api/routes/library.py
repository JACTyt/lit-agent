import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()
LIBRARY_DIR = Path("library")


def _read_meta(txt: Path) -> dict:
    meta_path = txt.with_suffix(".metadata.json")
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@router.get("/library")
async def list_library():
    if not LIBRARY_DIR.exists():
        return []
    return [
        {
            "book_name": txt.stem,
            "source_path": str(txt),
            "classification": _read_meta(txt).get("classification", {}),
            "version": _read_meta(txt).get("version", 1),
        }
        for txt in sorted(LIBRARY_DIR.glob("*.txt"))
    ]


@router.get("/library/{name}")
async def get_book(name: str):
    txt = LIBRARY_DIR / f"{name}.txt"
    if not txt.exists():
        raise HTTPException(status_code=404, detail=f"Book not found: {name}")
    meta = _read_meta(txt)
    return {"text": txt.read_text(encoding="utf-8"), **meta}


@router.get("/library/{name}/analysis")
async def get_analysis(name: str):
    meta_path = LIBRARY_DIR / f"{name}.metadata.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="No metadata for this book")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta.get("analysis", {})


@router.get("/library/{name}/characters")
async def get_characters(name: str):
    char_path = LIBRARY_DIR / f"{name}.characters.json"
    if not char_path.exists():
        raise HTTPException(status_code=404, detail="No character data for this book")
    return json.loads(char_path.read_text(encoding="utf-8"))
