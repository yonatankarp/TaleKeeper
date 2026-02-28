"""Transcript API endpoints."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from talekeeper.db import get_db

router = APIRouter(tags=["transcripts"])


class RetranscribeRequest(BaseModel):
    model_size: str = "medium"


@router.get("/api/sessions/{session_id}/transcript")
async def get_transcript(session_id: int) -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT ts.id, ts.session_id, ts.speaker_id, ts.text, ts.start_time, ts.end_time,
                      s.diarization_label, s.player_name, s.character_name
               FROM transcript_segments ts
               LEFT JOIN speakers s ON s.id = ts.speaker_id
               WHERE ts.session_id = ?
               ORDER BY ts.start_time""",
            (session_id,),
        )
    return [dict(r) for r in rows]


@router.post("/api/sessions/{session_id}/retranscribe")
async def retranscribe(session_id: int, body: RetranscribeRequest) -> dict:
    from talekeeper.services.audio import webm_to_wav
    from talekeeper.services.transcription import transcribe

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")

        session = dict(rows[0])
        if not session.get("audio_path"):
            raise HTTPException(status_code=400, detail="No audio recorded for this session")

        audio_path = Path(session["audio_path"])
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

    # Convert to WAV
    wav_path = audio_path.with_suffix(".wav")
    webm_to_wav(audio_path, wav_path)

    # Update status to transcribing
    async with get_db() as db:
        await db.execute(
            "UPDATE sessions SET status = 'transcribing', updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )

    # Transcribe
    segments = transcribe(wav_path, model_size=body.model_size)

    # Replace existing segments
    async with get_db() as db:
        await db.execute(
            "DELETE FROM transcript_segments WHERE session_id = ?", (session_id,)
        )

        for seg in segments:
            await db.execute(
                "INSERT INTO transcript_segments (session_id, text, start_time, end_time) VALUES (?, ?, ?, ?)",
                (session_id, seg.text, seg.start_time, seg.end_time),
            )

        await db.execute(
            "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )

    # Clean up WAV
    if wav_path.exists():
        wav_path.unlink()

    return {"segments_count": len(segments)}
