"""Speaker management API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from talekeeper.db import get_db

router = APIRouter(tags=["speakers"])


class SpeakerUpdate(BaseModel):
    player_name: str | None = None
    character_name: str | None = None


class SegmentSpeakerUpdate(BaseModel):
    speaker_id: int


class BulkReassign(BaseModel):
    segment_ids: list[int]
    speaker_id: int


@router.get("/api/sessions/{session_id}/speakers")
async def list_speakers(session_id: int) -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE session_id = ? ORDER BY diarization_label",
            (session_id,),
        )
    return [dict(r) for r in rows]


@router.put("/api/speakers/{speaker_id}")
async def update_speaker(speaker_id: int, body: SpeakerUpdate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE id = ?", (speaker_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Speaker not found")

        fields = []
        values = []
        if body.player_name is not None:
            fields.append("player_name = ?")
            values.append(body.player_name)
        if body.character_name is not None:
            fields.append("character_name = ?")
            values.append(body.character_name)

        if fields:
            values.append(speaker_id)
            await db.execute(
                f"UPDATE speakers SET {', '.join(fields)} WHERE id = ?",
                values,
            )

        rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE id = ?", (speaker_id,)
        )
    return dict(rows[0])


@router.put("/api/transcript-segments/{segment_id}/speaker")
async def reassign_segment_speaker(segment_id: int, body: SegmentSpeakerUpdate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM transcript_segments WHERE id = ?", (segment_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Segment not found")

        await db.execute(
            "UPDATE transcript_segments SET speaker_id = ? WHERE id = ?",
            (body.speaker_id, segment_id),
        )

        rows = await db.execute_fetchall(
            "SELECT * FROM transcript_segments WHERE id = ?", (segment_id,)
        )
    return dict(rows[0])


@router.put("/api/sessions/{session_id}/reassign-segments")
async def bulk_reassign_segments(session_id: int, body: BulkReassign) -> dict:
    async with get_db() as db:
        for seg_id in body.segment_ids:
            await db.execute(
                "UPDATE transcript_segments SET speaker_id = ? WHERE id = ? AND session_id = ?",
                (body.speaker_id, seg_id, session_id),
            )
    return {"updated": len(body.segment_ids)}


@router.get("/api/sessions/{session_id}/speaker-suggestions")
async def speaker_suggestions(session_id: int) -> list[dict]:
    """Return campaign roster entries for the speaker assignment dropdown."""
    async with get_db() as db:
        # Get campaign_id for the session
        rows = await db.execute_fetchall(
            "SELECT campaign_id FROM sessions WHERE id = ?", (session_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")

        campaign_id = rows[0]["campaign_id"]
        roster = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE campaign_id = ? AND is_active = 1 ORDER BY player_name",
            (campaign_id,),
        )
    return [dict(r) for r in roster]
