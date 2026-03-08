"""Voice signature API endpoints."""

import asyncio
import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from talekeeper.db import get_db
from talekeeper.services.diarization import extract_speaker_embedding

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


_MAX_VOICE_SAMPLE_SECONDS = 120  # 2 minutes


@router.post("/api/roster/{entry_id}/upload-voice-sample")
async def upload_voice_sample(entry_id: int, file: UploadFile) -> dict:
    """Upload an audio sample to create or replace a voice signature for a roster entry."""
    from pydub import AudioSegment

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, campaign_id FROM roster_entries WHERE id = ?", (entry_id,)
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Roster entry not found")

    campaign_id: int = rows[0]["campaign_id"]

    audio_bytes = await file.read()

    # Write upload to a temp file, convert to 16kHz mono WAV (truncated to max duration)
    tmp_input = tempfile.NamedTemporaryFile(delete=False)
    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        tmp_input.write(audio_bytes)
        tmp_input.flush()
        tmp_input.close()
        tmp_wav.close()

        try:
            audio = AudioSegment.from_file(tmp_input.name)
        except Exception:
            raise HTTPException(status_code=400, detail="Could not read audio file. Ensure it is a valid audio format.")

        max_ms = _MAX_VOICE_SAMPLE_SECONDS * 1000
        if len(audio) > max_ms:
            audio = audio[:max_ms]

        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(tmp_wav.name, format="wav")

        wav_path = Path(tmp_wav.name)
        embedding = await asyncio.to_thread(
            extract_speaker_embedding,
            wav_path,
            [(0.0, float(_MAX_VOICE_SAMPLE_SECONDS))],
        )
    finally:
        Path(tmp_input.name).unlink(missing_ok=True)
        Path(tmp_wav.name).unlink(missing_ok=True)

    if embedding is None:
        raise HTTPException(status_code=400, detail="No speech detected in uploaded audio.")

    embedding_json = json.dumps(embedding.tolist())

    async with get_db() as db:
        await db.execute(
            "DELETE FROM voice_signatures WHERE roster_entry_id = ?", (entry_id,)
        )
        cursor = await db.execute(
            """INSERT INTO voice_signatures
               (campaign_id, roster_entry_id, embedding, source_session_id, num_samples)
               VALUES (?, ?, ?, NULL, ?)""",
            (campaign_id, entry_id, embedding_json, len(embedding)),
        )
        sig_id = cursor.lastrowid
        rows = await db.execute_fetchall(
            "SELECT id, roster_entry_id, campaign_id, num_samples, created_at FROM voice_signatures WHERE id = ?",
            (sig_id,),
        )
    return dict(rows[0])


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
