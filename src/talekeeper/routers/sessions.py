"""Session CRUD API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from talekeeper.db import get_db

router = APIRouter(tags=["sessions"])


class SessionCreate(BaseModel):
    name: str
    date: str


class SessionUpdate(BaseModel):
    name: str | None = None
    date: str | None = None
    status: str | None = None


@router.post("/api/campaigns/{campaign_id}/sessions")
async def create_session(campaign_id: int, body: SessionCreate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT id FROM campaigns WHERE id = ?", (campaign_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, ?, ?)",
            (campaign_id, body.name, body.date),
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
            "SELECT * FROM sessions WHERE campaign_id = ? ORDER BY date DESC",
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
