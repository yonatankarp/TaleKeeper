"""Session CRUD API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from talekeeper.db import get_db
from talekeeper.services.transcription import SUPPORTED_LANGUAGES

router = APIRouter(tags=["sessions"])


class SessionCreate(BaseModel):
    name: str
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
            "SELECT id, language FROM campaigns WHERE id = ?", (campaign_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        language = body.language if body.language is not None else existing[0]["language"]

        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date, language) VALUES (?, ?, ?, ?)",
            (campaign_id, body.name, body.date, language),
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
