"""Image generation and management API endpoints."""

import json
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from pydantic import BaseModel
from typing import AsyncGenerator

from talekeeper.db import get_db
from talekeeper.services import llm_client, image_client
from talekeeper.services.image_generation import craft_scene_description, generate_session_image
from talekeeper.services.summarization import format_transcript

router = APIRouter(tags=["images"])


_SSE_PADDING = ":" + " " * 2048 + "\n"


def _sse_event(event: str, data: dict) -> str:
    """Format a server-sent event with padding to defeat output buffering."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n{_SSE_PADDING}"


class GenerateImageRequest(BaseModel):
    prompt: str | None = None


class CraftSceneRequest(BaseModel):
    pass


@router.post("/api/sessions/{session_id}/generate-image")
async def generate_image(session_id: int, body: GenerateImageRequest):
    """Generate an image for a session via SSE stream.

    Sends phase/done/error events so the frontend can show progress.
    """
    # --- Pre-flight checks (raise normal HTTP errors) ---
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")

    needs_crafting = body.prompt is None or body.prompt.strip() == ""

    if needs_crafting:
        llm_config = await llm_client.resolve_config()
        llm_health = await llm_client.health_check(llm_config["base_url"], llm_config["api_key"], llm_config["model"])
        if llm_health["status"] != "ok":
            raise HTTPException(status_code=503, detail=f"Text LLM unavailable: {llm_health.get('message', 'unknown error')}")

        content = await _get_session_content(session_id)
        if not content:
            raise HTTPException(status_code=400, detail="No transcript or summary available for this session")
    else:
        llm_config = None
        content = None

    img_config = await image_client.resolve_config()
    img_health = await image_client.health_check(img_config["base_url"], img_config["api_key"], img_config["model"])
    if img_health["status"] != "ok":
        raise HTTPException(status_code=503, detail=f"Image provider unavailable: {img_health.get('message', 'unknown error')}")

    # --- SSE generator (slow work happens here) ---
    async def _stream() -> AsyncGenerator[str, None]:
        try:
            prompt = body.prompt.strip() if body.prompt else ""
            scene_description = None

            if needs_crafting:
                yield _sse_event("phase", {"phase": "crafting_scene"})
                scene_description = await craft_scene_description(
                    content,
                    base_url=llm_config["base_url"],
                    api_key=llm_config["api_key"],
                    model=llm_config["model"],
                )
                prompt = scene_description

            yield _sse_event("phase", {"phase": "generating_image"})
            result = await generate_session_image(session_id, prompt, scene_description)
            yield _sse_event("done", {"image": result})
        except Exception as exc:
            traceback.print_exc()
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/sessions/{session_id}/craft-scene")
async def craft_scene(session_id: int) -> dict:
    """Craft a scene description from session content using the text LLM."""
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")

    llm_config = await llm_client.resolve_config()
    llm_health = await llm_client.health_check(llm_config["base_url"], llm_config["api_key"], llm_config["model"])
    if llm_health["status"] != "ok":
        raise HTTPException(status_code=503, detail=f"Text LLM unavailable: {llm_health.get('message', 'unknown error')}")

    content = await _get_session_content(session_id)
    if not content:
        raise HTTPException(status_code=400, detail="No transcript or summary available for this session")

    scene_description = await craft_scene_description(
        content,
        base_url=llm_config["base_url"],
        api_key=llm_config["api_key"],
        model=llm_config["model"],
    )
    return {"scene_description": scene_description}


@router.get("/api/sessions/{session_id}/images")
async def list_images(session_id: int) -> list[dict]:
    """List all images for a session, ordered by most recent first."""
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM session_images WHERE session_id = ? ORDER BY generated_at DESC",
            (session_id,),
        )
    return [dict(r) for r in rows]


@router.get("/api/images/{image_id}/file")
async def get_image_file(image_id: int):
    """Serve an image file."""
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM session_images WHERE id = ?", (image_id,)
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = Path(rows[0]["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    return FileResponse(file_path, media_type="image/png")


@router.delete("/api/images/{image_id}", status_code=204)
async def delete_image(image_id: int):
    """Delete an image file and its metadata."""
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM session_images WHERE id = ?", (image_id,)
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete file from disk
    file_path = Path(rows[0]["file_path"])
    if file_path.exists():
        file_path.unlink()

    # Clean up empty session directory
    parent = file_path.parent
    if parent.exists() and not any(parent.iterdir()):
        parent.rmdir()

    # Delete metadata from DB
    async with get_db() as db:
        await db.execute("DELETE FROM session_images WHERE id = ?", (image_id,))


@router.get("/api/settings/image-health")
async def image_health() -> dict:
    """Check image provider connectivity."""
    config = await image_client.resolve_config()
    return await image_client.health_check(config["base_url"], config["api_key"], config["model"])


async def _get_session_content(session_id: int) -> str | None:
    """Get session content for scene description generation.

    Prefers existing full summary; falls back to raw transcript.
    """
    async with get_db() as db:
        # Try existing full summary first
        summaries = await db.execute_fetchall(
            "SELECT content FROM summaries WHERE session_id = ? AND type = 'full' ORDER BY id DESC LIMIT 1",
            (session_id,),
        )
        if summaries and summaries[0]["content"]:
            return summaries[0]["content"]

        # Fall back to transcript
        segments = await db.execute_fetchall(
            """SELECT ts.text, ts.start_time, ts.end_time,
                      sp.diarization_label, sp.player_name, sp.character_name
               FROM transcript_segments ts
               LEFT JOIN speakers sp ON sp.id = ts.speaker_id
               WHERE ts.session_id = ?
               ORDER BY ts.start_time""",
            (session_id,),
        )

    if not segments:
        return None

    return format_transcript([dict(s) for s in segments])
