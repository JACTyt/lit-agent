import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routes import chat, library, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, chat.warmup)
    except Exception as exc:
        print(f"[startup] agent warmup failed — first /chat will be slow: {exc}")
    yield


app = FastAPI(title="Lit-Agent", version="2.0.0", lifespan=lifespan)

app.include_router(chat.router, prefix="/api")
app.include_router(library.router, prefix="/api")
app.include_router(system.router, prefix="/api")

FRONTEND_DIST = Path("frontend/dist")
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
