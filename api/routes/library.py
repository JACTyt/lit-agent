import json
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from rag.constants import LIBRARY_DIR

router = APIRouter()


# ── path safety ──────────────────────────────────────────────────────────────

def _safe_txt(name: str) -> Path:
    """Return the .txt Path and raise 400 if name could escape library/."""
    if not name or any(c in name for c in ('/', '\\', '\0')) or '..' in name:
        raise HTTPException(status_code=400, detail="Invalid book name")
    path = LIBRARY_DIR / f"{name}.txt"
    try:
        path.resolve().relative_to(LIBRARY_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book name")
    return path


# ── helpers ───────────────────────────────────────────────────────────────────

def _read_meta(txt: Path) -> dict:
    meta_path = txt.with_suffix(".metadata.json")
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── request models ────────────────────────────────────────────────────────────

class BookTextUpdate(BaseModel):
    text: str


class MetadataUpdate(BaseModel):
    classification: dict


class KeyMoment(BaseModel):
    moment: str
    explanation: str


class AnalysisUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    motivation: Optional[str] = None
    thesis: Optional[str] = None
    thoughts: Optional[list[str]] = None
    key_moments: Optional[list[KeyMoment]] = None
    brief_description: Optional[str] = None
    emotional_arc: Optional[str] = None


class WorldData(BaseModel):
    setting: str = ""
    time_period: str = ""
    tone: str = ""


class CharacterItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    role: str = ""
    traits: list[str] = []
    arc: str = ""
    first_appears: str = ""


class CharactersUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    version: int = 1
    story: str = ""
    extracted_at: str = ""
    world: WorldData = WorldData()
    characters: list[CharacterItem] = []


# ── routes ────────────────────────────────────────────────────────────────────

@router.get("/library")
async def list_library():
    if not LIBRARY_DIR.exists():
        return []
    result = []
    for txt in sorted(LIBRARY_DIR.glob("*.txt")):
        meta = _read_meta(txt)  # read once per book
        result.append({
            "book_name": txt.stem,
            "source_path": str(txt),
            "classification": meta.get("classification", {}),
            "version": meta.get("version", 1),
        })
    return result


@router.get("/library/{name}")
async def get_book(name: str):
    txt = _safe_txt(name)
    if not txt.exists():
        raise HTTPException(status_code=404, detail=f"Book not found: {name}")
    meta = _read_meta(txt)
    return {"text": txt.read_text(encoding="utf-8"), **meta}


@router.put("/library/{name}")
async def update_book_text(name: str, body: BookTextUpdate):
    txt = _safe_txt(name)
    if not txt.exists():
        raise HTTPException(status_code=404, detail=f"Book not found: {name}")
    txt.write_text(body.text, encoding="utf-8")
    return {"status": "saved", "book_name": name, "length": len(body.text)}


@router.put("/library/{name}/metadata")
async def update_metadata(name: str, body: MetadataUpdate):
    txt = _safe_txt(name)
    if not txt.exists():
        raise HTTPException(status_code=404, detail=f"Book not found: {name}")
    meta_path = txt.with_suffix(".metadata.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta["classification"] = body.classification
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "saved"}


@router.put("/library/{name}/analysis")
async def update_analysis(name: str, body: AnalysisUpdate):
    txt = _safe_txt(name)
    if not txt.exists():
        raise HTTPException(status_code=404, detail=f"Book not found: {name}")
    meta_path = txt.with_suffix(".metadata.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta["analysis"] = body.model_dump()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "saved"}


@router.put("/library/{name}/characters")
async def update_characters(name: str, body: CharactersUpdate):
    txt = _safe_txt(name)
    if not txt.exists():
        raise HTTPException(status_code=404, detail=f"Book not found: {name}")
    char_path = txt.with_suffix(".characters.json")
    char_path.write_text(
        json.dumps(body.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"status": "saved"}


@router.get("/library/{name}/analysis")
async def get_analysis(name: str):
    txt = _safe_txt(name)
    meta_path = txt.with_suffix(".metadata.json")
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="No metadata for this book")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta.get("analysis", {})


@router.get("/library/{name}/characters")
async def get_characters(name: str):
    txt = _safe_txt(name)
    char_path = txt.with_suffix(".characters.json")
    if not char_path.exists():
        raise HTTPException(status_code=404, detail="No character data for this book")
    return json.loads(char_path.read_text(encoding="utf-8"))
