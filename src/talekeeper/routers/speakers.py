"""Speaker management API endpoints."""

import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from talekeeper.db import get_db

router = APIRouter(tags=["speakers"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class SpeakerUpdate(BaseModel):
    player_name: str | None = None
    character_name: str | None = None


class SegmentSpeakerUpdate(BaseModel):
    speaker_id: int


class BulkReassign(BaseModel):
    segment_ids: list[int]
    speaker_id: int


class MergeSpeakers(BaseModel):
    source_speaker_id: int
    target_speaker_id: int


class ReDiarizeRequest(BaseModel):
    num_speakers: int = Field(ge=1, le=10)


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


@router.post("/api/sessions/{session_id}/merge-speakers")
async def merge_speakers(session_id: int, body: MergeSpeakers) -> dict:
    """Merge source speaker into target speaker within a session.

    Reassigns all transcript segments from source to target, cleans up
    the source speaker's voice signature if one exists, then deletes the
    source speaker record. The entire operation is atomic.
    """
    if body.source_speaker_id == body.target_speaker_id:
        raise HTTPException(
            status_code=400, detail="Source and target speakers must be different"
        )

    async with get_db() as db:
        # Fetch both speakers
        source_rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE id = ?", (body.source_speaker_id,)
        )
        if not source_rows:
            raise HTTPException(status_code=404, detail="Source speaker not found")
        source = dict(source_rows[0])

        target_rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE id = ?", (body.target_speaker_id,)
        )
        if not target_rows:
            raise HTTPException(status_code=404, detail="Target speaker not found")
        target = dict(target_rows[0])

        # Validate both belong to the same session matching the URL param
        if source["session_id"] != session_id:
            raise HTTPException(
                status_code=400,
                detail="Source speaker does not belong to this session",
            )
        if target["session_id"] != session_id:
            raise HTTPException(
                status_code=400,
                detail="Target speaker does not belong to this session",
            )

        # Reassign all transcript segments from source to target
        await db.execute(
            "UPDATE transcript_segments SET speaker_id = ? WHERE speaker_id = ?",
            (body.target_speaker_id, body.source_speaker_id),
        )

        # Clean up source speaker's voice signature if one exists
        if source["player_name"] and source["character_name"]:
            # Look up the campaign for this session
            session_rows = await db.execute_fetchall(
                "SELECT campaign_id FROM sessions WHERE id = ?", (session_id,)
            )
            if session_rows:
                campaign_id = session_rows[0]["campaign_id"]
                # Find the roster entry matching the source speaker
                roster_rows = await db.execute_fetchall(
                    "SELECT id FROM roster_entries WHERE campaign_id = ? AND player_name = ? AND character_name = ?",
                    (campaign_id, source["player_name"], source["character_name"]),
                )
                if roster_rows:
                    roster_entry_id = roster_rows[0]["id"]
                    await db.execute(
                        "DELETE FROM voice_signatures WHERE roster_entry_id = ?",
                        (roster_entry_id,),
                    )

        # Delete the source speaker
        await db.execute(
            "DELETE FROM speakers WHERE id = ?", (body.source_speaker_id,)
        )

        # Return target speaker with segment count
        target_rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE id = ?", (body.target_speaker_id,)
        )
        target = dict(target_rows[0])

        count_rows = await db.execute_fetchall(
            "SELECT COUNT(*) as count FROM transcript_segments WHERE speaker_id = ?",
            (body.target_speaker_id,),
        )
        target["segment_count"] = count_rows[0]["count"]

    return target


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


@router.post("/api/sessions/{session_id}/re-diarize")
async def re_diarize(session_id: int, body: ReDiarizeRequest) -> StreamingResponse:
    """Re-run speaker diarization on a completed session without re-transcribing."""
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")

        session = dict(rows[0])
        if not session.get("audio_path"):
            raise HTTPException(
                status_code=400, detail="No audio recorded for this session"
            )

        if session.get("status") not in ("completed",):
            raise HTTPException(
                status_code=409, detail="Session is currently being processed"
            )

        audio_path = Path(session["audio_path"])
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

    async def sse_generator() -> AsyncIterator[str]:
        try:
            # Set status to diarizing
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'diarizing', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

            yield _sse_event("phase", {"phase": "diarization"})

            # Cleanup: delete diarization-split children so original rows are restored,
            # then reset speaker assignments on the originals
            async with get_db() as db:
                await db.execute(
                    "DELETE FROM transcript_segments WHERE session_id = ? AND parent_segment_id IS NOT NULL",
                    (session_id,),
                )
                await db.execute(
                    "UPDATE transcript_segments SET speaker_id = NULL, is_overlap = 0 WHERE session_id = ?",
                    (session_id,),
                )

            # Cleanup: delete voice signatures sourced from this session
            async with get_db() as db:
                await db.execute(
                    "DELETE FROM voice_signatures WHERE source_session_id = ?",
                    (session_id,),
                )

            # Cleanup: delete all speakers for the session
            async with get_db() as db:
                await db.execute(
                    "DELETE FROM speakers WHERE session_id = ?",
                    (session_id,),
                )

            # Convert audio to WAV and run diarization with progress
            from talekeeper.services.audio import audio_to_wav
            from talekeeper.services.diarization import run_final_diarization

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

            wav_path = audio_to_wav(audio_path)
            try:
                await run_final_diarization(
                    session_id,
                    wav_path,
                    num_speakers_override=body.num_speakers,
                    progress_callback=_diarization_progress,
                )
            finally:
                if wav_path.exists():
                    wav_path.unlink()

            for evt in progress_events:
                yield evt

            # Count segments for the done event
            async with get_db() as db:
                count_rows = await db.execute_fetchall(
                    "SELECT COUNT(*) as count FROM transcript_segments WHERE session_id = ?",
                    (session_id,),
                )
                segments_count = count_rows[0]["count"]

            # Mark session as completed
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

            yield _sse_event("done", {"segments_count": segments_count})

        except Exception as exc:
            yield _sse_event("error", {"message": str(exc)})
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
