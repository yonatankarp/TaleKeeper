"""FastAPI application for TaleKeeper."""

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from talekeeper.db import init_db
from talekeeper.routers import campaigns, sessions, roster, recording, transcripts, speakers, summaries, exports, settings, voice_signatures


def _cleanup_orphaned_chunk_dirs() -> None:
    """Delete any orphaned tmp_* directories under data/audio/."""
    import shutil

    audio_root = Path("data/audio")
    if not audio_root.exists():
        return
    for campaign_dir in audio_root.iterdir():
        if not campaign_dir.is_dir():
            continue
        for item in campaign_dir.iterdir():
            if item.is_dir() and item.name.startswith("tmp_"):
                shutil.rmtree(item, ignore_errors=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    _cleanup_orphaned_chunk_dirs()
    yield


app = FastAPI(title="TaleKeeper", version="0.1.0", lifespan=lifespan)

_cors_extra = os.environ.get("TALEKEEPER_CORS_ORIGINS", "")
_cors_origins = ["http://localhost:5173"]
if _cors_extra:
    _cors_origins.extend(origin.strip() for origin in _cors_extra.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns.router)
app.include_router(sessions.router)
app.include_router(roster.router)
app.include_router(recording.router)
app.include_router(transcripts.router)
app.include_router(speakers.router)
app.include_router(summaries.router)
app.include_router(exports.router)
app.include_router(settings.router)
app.include_router(voice_signatures.router)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/setup-status")
async def setup_status() -> dict:
    from talekeeper.services.setup import check_first_run
    return await check_first_run()


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
