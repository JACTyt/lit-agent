import json
import os

from fastapi import APIRouter, HTTPException

from agent.llm_provider import get_llm_provider, get_chat_model_name
from rag.ingest import ingest_books

router = APIRouter()


@router.get("/health")
async def health():
    return {"provider": get_llm_provider(), "model": get_chat_model_name(), "status": "ok"}


@router.post("/reimport")
async def reimport():
    _, count = ingest_books()
    return {"status": "ok", "vectors": count}


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    path = os.path.join("sessions", f"session_{session_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Session not found")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
