"""Session CRUD API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from talekeeper.db import get_db
from talekeeper.services.transcription import SUPPORTED_LANGUAGES

router = APIRouter(tags=["sessions"])


class SessionCreate(BaseModel):
    name: str | None = None
    date: str
    language: str | None = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}")
        return v


class SessionUpdate(BaseModel):
    name: str | None = None
    date: str | None = None
    status: str | None = None
    language: str | None = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}")
        return v


@router.post("/api/campaigns/{campaign_id}/sessions")
async def create_session(campaign_id: int, body: SessionCreate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT id, language, session_start_number FROM campaigns WHERE id = ?",
            (campaign_id,),
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        campaign = existing[0]
        language = body.language if body.language is not None else campaign["language"]

        # Auto-assign session_number: max of (next sequential, campaign start number)
        max_row = await db.execute_fetchall(
            "SELECT MAX(session_number) as max_num FROM sessions WHERE campaign_id = ?",
            (campaign_id,),
        )
        max_num = max_row[0]["max_num"]
        next_sequential = (max_num + 1) if max_num is not None else 0
        session_number = max(next_sequential, campaign["session_start_number"])

        # Auto-set name if not provided
        name = body.name if body.name else f"Session {session_number}"

        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date, language, session_number) VALUES (?, ?, ?, ?, ?)",
            (campaign_id, name, body.date, language, session_number),
        )
        session_id = cursor.lastrowid
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
    return dict(rows[0])


@router.get("/api/campaigns/{campaign_id}/sessions")
async def list_sessions(campaign_id: int) -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT s.*,
                      (SELECT COUNT(*) FROM transcript_segments ts WHERE ts.session_id = s.id) AS transcript_count,
                      (SELECT COUNT(*) FROM summaries sm WHERE sm.session_id = s.id) AS summary_count,
                      (SELECT COUNT(*) FROM session_images si WHERE si.session_id = s.id) AS image_count
               FROM sessions s
               WHERE s.campaign_id = ?
               ORDER BY s.date DESC""",
            (campaign_id,),
        )
    return [dict(r) for r in rows]


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: int) -> dict:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(rows[0])


@router.put("/api/sessions/{session_id}")
async def update_session(session_id: int, body: SessionUpdate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Session not found")

        fields = []
        values = []
        if body.name is not None:
            fields.append("name = ?")
            values.append(body.name)
        if body.date is not None:
            fields.append("date = ?")
            values.append(body.date)
        if body.status is not None:
            fields.append("status = ?")
            values.append(body.status)
        if body.language is not None:
            fields.append("language = ?")
            values.append(body.language)

        if fields:
            fields.append("updated_at = datetime('now')")
            values.append(session_id)
            await db.execute(
                f"UPDATE sessions SET {', '.join(fields)} WHERE id = ?",
                values,
            )

        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
    return dict(rows[0])


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: int) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Session not found")

        session = dict(existing[0])

        # Delete audio file if it exists
        if session.get("audio_path"):
            from pathlib import Path

            path = Path(session["audio_path"])
            if path.exists():
                path.unlink()

        # Cascade deletes handle DB records
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    return {"deleted": True}


@router.post("/api/sessions/{session_id}/generate-name")
async def generate_name(session_id: int) -> dict:
    """Trigger LLM-based session name generation. Prefers summary over transcript."""
    from talekeeper.services.session_naming import generate_session_name, _get_summary_text
    from talekeeper.services.summarization import format_transcript

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")

        session = dict(rows[0])

        summary_text = await _get_summary_text(db, session_id)

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
            raise HTTPException(
                status_code=400,
                detail="Session has no transcript segments",
            )

    if summary_text:
        title = await generate_session_name(summary_text, from_summary=True)
    else:
        transcript_text = format_transcript([dict(s) for s in segments])
        title = await generate_session_name(transcript_text)

    session_number = session["session_number"]
    new_name = f"Session {session_number}: {title}" if session_number is not None else title

    async with get_db() as db:
        await db.execute(
            "UPDATE sessions SET name = ?, updated_at = datetime('now') WHERE id = ?",
            (new_name, session_id),
        )
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
    return dict(rows[0])
