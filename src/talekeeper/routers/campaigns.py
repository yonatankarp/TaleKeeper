"""Campaign CRUD API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from talekeeper.db import get_db
from talekeeper.services.transcription import SUPPORTED_LANGUAGES

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    language: str = "en"

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

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}")
        return v


@router.post("")
async def create_campaign(body: CampaignCreate) -> dict:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO campaigns (name, description, language) VALUES (?, ?, ?)",
            (body.name, body.description, body.language),
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

        if fields:
            fields.append("updated_at = datetime('now')")
            values.append(campaign_id)
            await db.execute(
                f"UPDATE campaigns SET {', '.join(fields)} WHERE id = ?",
                values,
            )

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
        audio_dir = Path(f"data/audio/{campaign_id}")
        if audio_dir.exists():
            import shutil
            shutil.rmtree(audio_dir)

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
