from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routes import chat, library, system

app = FastAPI(title="Lit-Agent", version="2.0.0")

app.include_router(chat.router, prefix="/api")
app.include_router(library.router, prefix="/api")
app.include_router(system.router, prefix="/api")

FRONTEND_DIST = Path("frontend/dist")
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
