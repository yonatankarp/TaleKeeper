"""Campaign CRUD API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from talekeeper.db import get_db
from talekeeper.paths import get_campaign_audio_dir
from talekeeper.services.transcription import SUPPORTED_LANGUAGES

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    language: str = "en"
    num_speakers: int = Field(default=5, ge=1, le=10)
    session_start_number: int = 0

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}")
        return v


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    language: str | None = None
    num_speakers: int | None = Field(default=None, ge=1, le=10)
    session_start_number: int | None = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}")
        return v


async def _renumber_sessions(
    db, campaign_id: int, start_number: int
) -> None:
    """Renumber all sessions in a campaign starting from start_number.

    Updates session_number and auto-generated names (Session N / Session N: Title).
    """
    import re

    pattern = re.compile(r"^Session \d+(?:\s*:\s*(.+))?$")

    sessions = await db.execute_fetchall(
        "SELECT id, name, session_number FROM sessions WHERE campaign_id = ? "
        "ORDER BY session_number ASC, created_at ASC, id ASC",
        (campaign_id,),
    )
    for i, session in enumerate(sessions):
        new_number = start_number + i
        if new_number == session["session_number"]:
            continue

        # Update the session number
        await db.execute(
            "UPDATE sessions SET session_number = ? WHERE id = ?",
            (new_number, session["id"]),
        )

        # Update auto-generated names: "Session N" → "Session M" or "Session N: Title" → "Session M: Title"
        name = session["name"] or ""
        match = pattern.match(name.strip())
        if match:
            title_part = match.group(1)
            new_name = f"Session {new_number}: {title_part}" if title_part else f"Session {new_number}"
            await db.execute(
                "UPDATE sessions SET name = ? WHERE id = ?",
                (new_name, session["id"]),
            )


@router.post("")
async def create_campaign(body: CampaignCreate) -> dict:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO campaigns (name, description, language, num_speakers, session_start_number) VALUES (?, ?, ?, ?, ?)",
            (body.name, body.description, body.language, body.num_speakers, body.session_start_number),
        )
        campaign_id = cursor.lastrowid
        row = await db.execute_fetchall(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        )
    return dict(row[0])


@router.get("")
async def list_campaigns() -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM campaigns ORDER BY updated_at DESC"
        )
    return [dict(r) for r in rows]


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int) -> dict:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return dict(rows[0])


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: int, body: CampaignUpdate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        fields = []
        values = []
        if body.name is not None:
            fields.append("name = ?")
            values.append(body.name)
        if body.description is not None:
            fields.append("description = ?")
            values.append(body.description)
        if body.language is not None:
            fields.append("language = ?")
            values.append(body.language)
        if body.num_speakers is not None:
            fields.append("num_speakers = ?")
            values.append(body.num_speakers)
        if body.session_start_number is not None:
            fields.append("session_start_number = ?")
            values.append(body.session_start_number)

        if fields:
            fields.append("updated_at = datetime('now')")
            values.append(campaign_id)
            await db.execute(
                f"UPDATE campaigns SET {', '.join(fields)} WHERE id = ?",
                values,
            )

        # Renumber sessions when session_start_number changes
        if body.session_start_number is not None:
            await _renumber_sessions(db, campaign_id, body.session_start_number)

        rows = await db.execute_fetchall(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        )
    return dict(rows[0])


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Delete audio files for all sessions in this campaign
        sessions = await db.execute_fetchall(
            "SELECT audio_path FROM sessions WHERE campaign_id = ? AND audio_path IS NOT NULL",
            (campaign_id,),
        )
        from pathlib import Path

        for s in sessions:
            path = Path(s["audio_path"])
            if path.exists():
                path.unlink()

        # Cascade deletes handle DB records (FK ON DELETE CASCADE)
        await db.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))

        # Clean up campaign audio directory
        campaign_audio = get_campaign_audio_dir(campaign_id)
        if campaign_audio.exists():
            import shutil
            shutil.rmtree(campaign_audio)

    return {"deleted": True}


@router.get("/{campaign_id}/dashboard")
async def campaign_dashboard(campaign_id: int) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        session_count = await db.execute_fetchall(
            "SELECT COUNT(*) as count FROM sessions WHERE campaign_id = ?",
            (campaign_id,),
        )

        # Total recorded time from transcript segments
        total_time = await db.execute_fetchall(
            """SELECT COALESCE(MAX(ts.end_time), 0) as total
               FROM sessions s
               LEFT JOIN transcript_segments ts ON ts.session_id = s.id
               WHERE s.campaign_id = ?""",
            (campaign_id,),
        )

        most_recent = await db.execute_fetchall(
            "SELECT date FROM sessions WHERE campaign_id = ? ORDER BY date DESC LIMIT 1",
            (campaign_id,),
        )

    return {
        "session_count": session_count[0]["count"],
        "total_recorded_time": total_time[0]["total"],
        "most_recent_session_date": most_recent[0]["date"] if most_recent else None,
    }
