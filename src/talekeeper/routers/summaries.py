"""Summary generation and management API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from talekeeper.db import get_db
from talekeeper.services import llm_client
from talekeeper.services.summarization import (
    format_transcript,
    generate_full_summary,
    generate_pov_summary,
)

router = APIRouter(tags=["summaries"])


class GenerateSummaryRequest(BaseModel):
    type: str = "full"  # "full" or "pov"


class SummaryUpdate(BaseModel):
    content: str


@router.get("/api/sessions/{session_id}/summaries")
async def list_summaries(session_id: int) -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT su.*, sp.character_name, sp.player_name
               FROM summaries su
               LEFT JOIN speakers sp ON sp.id = su.speaker_id
               WHERE su.session_id = ?
               ORDER BY su.type, su.id""",
            (session_id,),
        )
    return [dict(r) for r in rows]


@router.post("/api/sessions/{session_id}/generate-summary")
async def generate_summary(session_id: int, body: GenerateSummaryRequest) -> dict:
    # Resolve LLM config
    config = await llm_client.resolve_config()
    base_url, api_key, model = config["base_url"], config["api_key"], config["model"]

    # Check LLM connectivity
    health = await llm_client.health_check(base_url, api_key, model)
    if health["status"] != "ok":
        raise HTTPException(status_code=503, detail=health["message"])

    # Get transcript
    async with get_db() as db:
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
        raise HTTPException(status_code=400, detail="No transcript available for this session")

    transcript_text = format_transcript([dict(s) for s in segments])

    if body.type == "full":
        content = await generate_full_summary(transcript_text, base_url=base_url, api_key=api_key, model=model)

        async with get_db() as db:
            cursor = await db.execute(
                "INSERT INTO summaries (session_id, type, content, model_used) VALUES (?, 'full', ?, ?)",
                (session_id, content, model),
            )
            rows = await db.execute_fetchall(
                "SELECT * FROM summaries WHERE id = ?", (cursor.lastrowid,)
            )
        return dict(rows[0])

    elif body.type == "pov":
        # Generate one POV per named speaker
        async with get_db() as db:
            speakers = await db.execute_fetchall(
                "SELECT * FROM speakers WHERE session_id = ? AND character_name IS NOT NULL",
                (session_id,),
            )

        if not speakers:
            raise HTTPException(
                status_code=400,
                detail="No speakers have been assigned character names. Assign names first.",
            )

        results = []
        for speaker in speakers:
            sp = dict(speaker)
            content = await generate_pov_summary(
                transcript_text,
                character_name=sp["character_name"],
                player_name=sp["player_name"] or "Unknown",
                base_url=base_url,
                api_key=api_key,
                model=model,
            )

            async with get_db() as db:
                cursor = await db.execute(
                    "INSERT INTO summaries (session_id, type, speaker_id, content, model_used) VALUES (?, 'pov', ?, ?, ?)",
                    (session_id, sp["id"], content, model),
                )
                rows = await db.execute_fetchall(
                    "SELECT * FROM summaries WHERE id = ?", (cursor.lastrowid,)
                )
            results.append(dict(rows[0]))

        return {"summaries": results}

    raise HTTPException(status_code=400, detail="Invalid summary type. Use 'full' or 'pov'.")


@router.get("/api/summaries/{summary_id}")
async def get_summary(summary_id: int) -> dict:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM summaries WHERE id = ?", (summary_id,)
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Summary not found")
    return dict(rows[0])


@router.put("/api/summaries/{summary_id}")
async def update_summary(summary_id: int, body: SummaryUpdate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM summaries WHERE id = ?", (summary_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Summary not found")

        await db.execute(
            "UPDATE summaries SET content = ? WHERE id = ?",
            (body.content, summary_id),
        )
        rows = await db.execute_fetchall(
            "SELECT * FROM summaries WHERE id = ?", (summary_id,)
        )
    return dict(rows[0])


@router.delete("/api/summaries/{summary_id}")
async def delete_summary(summary_id: int) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM summaries WHERE id = ?", (summary_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Summary not found")

        await db.execute("DELETE FROM summaries WHERE id = ?", (summary_id,))
    return {"deleted": True}


@router.post("/api/sessions/{session_id}/regenerate-summary")
async def regenerate_summary(session_id: int, body: GenerateSummaryRequest) -> dict:
    """Delete existing summaries of the given type and regenerate."""
    async with get_db() as db:
        await db.execute(
            "DELETE FROM summaries WHERE session_id = ? AND type = ?",
            (session_id, body.type),
        )

    return await generate_summary(session_id, body)


@router.get("/api/llm/status")
async def llm_status() -> dict:
    config = await llm_client.resolve_config()
    return await llm_client.health_check(config["base_url"], config["api_key"], config["model"])
