"""Transcript API endpoints."""

import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from talekeeper.db import get_db
from talekeeper.services.transcription import SUPPORTED_LANGUAGES

router = APIRouter(tags=["transcripts"])


class RetranscribeRequest(BaseModel):
    model_size: str = "medium"
    language: str | None = None
    num_speakers: int | None = Field(default=None, ge=1, le=10)

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}")
        return v


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


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/api/sessions/{session_id}/retranscribe")
async def retranscribe(session_id: int, body: RetranscribeRequest) -> StreamingResponse:
    from talekeeper.services.transcription import (
        transcribe_chunked,
        TranscriptSegment,
        ChunkProgress,
    )

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

        language = body.language if body.language is not None else session.get("language", "en")
        num_speakers_override = body.num_speakers

    async def sse_generator() -> AsyncIterator[str]:
        segments_count = 0
        try:
            # Delete existing segments and speakers, set status to transcribing
            async with get_db() as db:
                await db.execute(
                    "DELETE FROM transcript_segments WHERE session_id = ?", (session_id,)
                )
                await db.execute(
                    "DELETE FROM speakers WHERE session_id = ?", (session_id,)
                )
                await db.execute(
                    "UPDATE sessions SET status = 'transcribing', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

            for item in transcribe_chunked(audio_path, model_size=body.model_size, language=language):
                if isinstance(item, ChunkProgress):
                    yield _sse_event("progress", {
                        "chunk": item.chunk,
                        "total_chunks": item.total_chunks,
                    })
                elif isinstance(item, TranscriptSegment):
                    # Persist segment before emitting SSE event
                    async with get_db() as db:
                        await db.execute(
                            "INSERT INTO transcript_segments (session_id, text, start_time, end_time) VALUES (?, ?, ?, ?)",
                            (session_id, item.text, item.start_time, item.end_time),
                        )

                    yield _sse_event("segment", {
                        "text": item.text,
                        "start_time": item.start_time,
                        "end_time": item.end_time,
                    })
                    segments_count += 1

            # Run speaker diarization before marking complete
            from talekeeper.services.diarization import run_final_diarization
            from talekeeper.services.audio import webm_to_wav
            wav_path = webm_to_wav(audio_path)
            try:
                await run_final_diarization(session_id, wav_path, num_speakers_override=num_speakers_override)
            finally:
                if wav_path.exists():
                    wav_path.unlink()

            # Mark session as completed
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

            yield _sse_event("done", {"segments_count": segments_count})

        except Exception as exc:
            # Emit error event and recover session status
            yield _sse_event("error", {"message": str(exc)})
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
