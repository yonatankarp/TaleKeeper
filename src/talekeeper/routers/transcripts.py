"""Transcript API endpoints."""

import asyncio
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
    model_name: str | None = None
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
                      ts.is_overlap, s.diarization_label, s.player_name, s.character_name
               FROM transcript_segments ts
               LEFT JOIN speakers s ON s.id = ts.speaker_id
               WHERE ts.session_id = ?
                 AND (
                   ts.parent_segment_id IS NOT NULL
                   OR NOT EXISTS (
                     SELECT 1 FROM transcript_segments c
                     WHERE c.parent_segment_id = ts.id
                   )
                 )
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

            kwargs = {"language": language}
            if body.model_name:
                kwargs["model_name"] = body.model_name
            for item in transcribe_chunked(audio_path, **kwargs):
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

            # Run speaker diarization with progress before marking complete
            from talekeeper.services.diarization import run_final_diarization
            from talekeeper.services.audio import webm_to_wav

            yield _sse_event("phase", {"phase": "diarization"})

            progress_events: list[str] = []

            def _diarization_progress(stage: str, detail: dict) -> None:
                if stage == "vad_start":
                    progress_events.append(_sse_event("progress", {"detail": "Detecting speech activity..."}))
                elif stage == "vad_done":
                    n = detail["num_segments"]
                    secs = int(detail["total_speech_seconds"])
                    progress_events.append(_sse_event("progress", {"detail": f"Found {n} speech segments ({secs}s of speech)"}))
                elif stage == "change_detection_start":
                    progress_events.append(_sse_event("progress", {"detail": "Detecting speaker changes..."}))
                elif stage == "change_detection_done":
                    n = detail["num_segments_processed"]
                    c = detail["num_changes_found"]
                    progress_events.append(_sse_event("progress", {"detail": f"Found {c} speaker changes in {n} segments"}))
                elif stage == "embeddings":
                    cur, total = detail["current"], detail["total"]
                    if cur % max(1, total // 20) == 0 or cur == total:
                        progress_events.append(_sse_event("progress", {"detail": f"Extracting speaker embeddings ({cur}/{total})..."}))
                elif stage == "clustering_done":
                    ns = detail["num_speakers"]
                    nseg = detail["num_segments"]
                    progress_events.append(_sse_event("progress", {"detail": f"Found {ns} speakers, {nseg} segments"}))

            wav_path = webm_to_wav(audio_path)
            try:
                await run_final_diarization(session_id, wav_path, num_speakers_override=num_speakers_override, progress_callback=_diarization_progress)
            finally:
                if wav_path.exists():
                    wav_path.unlink()

            for evt in progress_events:
                yield evt

            # Mark session as completed
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

            yield _sse_event("done", {"segments_count": segments_count})

            # Fire-and-forget: generate session name from transcript
            from talekeeper.services.session_naming import maybe_generate_and_update_name
            asyncio.create_task(maybe_generate_and_update_name(session_id))

        except Exception as exc:
            # Emit error event and recover session status
            yield _sse_event("error", {"message": str(exc)})
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
