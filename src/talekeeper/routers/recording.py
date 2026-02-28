"""WebSocket recording endpoint and audio management."""

import asyncio
import io
import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse

from talekeeper.db import get_db

router = APIRouter(tags=["recording"])

# Track active recording session (in-process lock)
_active_recording_session: int | None = None


async def _run_transcription_on_chunk(
    accumulated_audio: bytes, session_id: int, websocket: WebSocket, offset: float
) -> None:
    """Run incremental transcription on accumulated audio and stream results back."""
    try:
        from talekeeper.services.audio import webm_bytes_to_wav
        from talekeeper.services.transcription import transcribe

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        webm_bytes_to_wav(accumulated_audio, wav_path)

        segments = transcribe(wav_path)

        for seg in segments:
            if seg.start_time >= offset:
                await websocket.send_json({
                    "type": "transcript",
                    "text": seg.text,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                })

                # Persist segment
                async with get_db() as db:
                    await db.execute(
                        "INSERT INTO transcript_segments (session_id, text, start_time, end_time) VALUES (?, ?, ?, ?)",
                        (session_id, seg.text, seg.start_time, seg.end_time),
                    )

        if wav_path.exists():
            wav_path.unlink()
    except Exception:
        pass  # Don't crash the recording if transcription fails


@router.websocket("/ws/recording/{session_id}")
async def recording_ws(websocket: WebSocket, session_id: int) -> None:
    global _active_recording_session

    await websocket.accept()

    if _active_recording_session is not None and _active_recording_session != session_id:
        await websocket.send_json({"type": "error", "message": "Another session is recording"})
        await websocket.close()
        return

    # Look up the session to get campaign_id
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        if not rows:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close()
            return

        session = dict(rows[0])
        campaign_id = session["campaign_id"]

        # Update session status to recording
        await db.execute(
            "UPDATE sessions SET status = 'recording', updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )

    _active_recording_session = session_id

    # Prepare audio path
    audio_dir = Path(f"data/audio/{campaign_id}")
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{session_id}.webm"

    chunks: list[bytes] = []
    chunk_count = 0
    last_transcribed_offset = 0.0

    try:
        while True:
            data = await websocket.receive()

            if "bytes" in data:
                chunks.append(data["bytes"])
                chunk_count += 1

                # Run incremental transcription every ~10 seconds of audio
                if chunk_count % 10 == 0 and chunks:
                    accumulated = b"".join(chunks)
                    asyncio.create_task(
                        _run_transcription_on_chunk(
                            accumulated, session_id, websocket, last_transcribed_offset
                        )
                    )
            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "stop":
                    break
    except WebSocketDisconnect:
        pass
    finally:
        _active_recording_session = None

        # Assemble chunks into a single file
        if chunks:
            with open(audio_path, "wb") as f:
                for chunk in chunks:
                    f.write(chunk)

            # Update session with audio path and status
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET audio_path = ?, status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (str(audio_path), session_id),
                )
        else:
            # No audio recorded, revert to draft
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'draft', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )


@router.get("/api/sessions/{session_id}/audio")
async def get_session_audio(session_id: int) -> FileResponse:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT audio_path FROM sessions WHERE id = ?", (session_id,)
        )
    if not rows or not rows[0]["audio_path"]:
        raise HTTPException(status_code=404, detail="No audio for this session")

    audio_path = Path(rows[0]["audio_path"])
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        audio_path,
        media_type="audio/webm",
        headers={"Accept-Ranges": "bytes"},
    )
