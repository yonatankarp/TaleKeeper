"""Voice signature API endpoints."""

from fastapi import APIRouter, HTTPException

from talekeeper.db import get_db

router = APIRouter(tags=["voice-signatures"])


@router.post("/api/sessions/{session_id}/generate-voice-signatures")
async def generate_voice_signatures(session_id: int) -> dict:
    """Generate voice signatures from a labeled session."""
    from talekeeper.services.diarization import generate_voice_signatures as _generate

    async with get_db() as db:
        session = await db.execute_fetchall(
            "SELECT id, audio_path FROM sessions WHERE id = ?", (session_id,)
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if not session[0]["audio_path"]:
            raise HTTPException(status_code=400, detail="Session has no audio")

    try:
        results = await _generate(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "signatures_generated": len(results),
        "speakers": results,
    }


@router.get("/api/campaigns/{campaign_id}/voice-signatures")
async def list_voice_signatures(campaign_id: int) -> list[dict]:
    """List voice signatures for a campaign (without raw embeddings)."""
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT id FROM campaigns WHERE id = ?", (campaign_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        rows = await db.execute_fetchall(
            """SELECT vs.id, vs.campaign_id, vs.roster_entry_id, vs.source_session_id,
                      vs.num_samples, vs.created_at,
                      r.player_name, r.character_name
               FROM voice_signatures vs
               JOIN roster_entries r ON r.id = vs.roster_entry_id
               WHERE vs.campaign_id = ?
               ORDER BY r.player_name""",
            (campaign_id,),
        )
    return [dict(r) for r in rows]


@router.delete("/api/voice-signatures/{signature_id}")
async def delete_voice_signature(signature_id: int) -> dict:
    """Delete a specific voice signature."""
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT id FROM voice_signatures WHERE id = ?", (signature_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Voice signature not found")

        await db.execute("DELETE FROM voice_signatures WHERE id = ?", (signature_id,))
    return {"deleted": True}
