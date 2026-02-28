"""WebSocket recording endpoint and audio management."""

import asyncio
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
    chunk_dir: Path,
    current_chunk_index: int,
    session_id: int,
    websocket: WebSocket,
    cumulative_offset: float,
    language: str = "en",
) -> float:
    """Transcribe the new audio since the last transcription.

    Concatenates all chunks from 0 (for valid WebM header) to current,
    converts to WAV, slices from cumulative_offset onwards, and transcribes
    only the new portion. Returns the new cumulative offset.
    """
    try:
        import io
        from pydub import AudioSegment
        from talekeeper.services.transcription import transcribe

        # Concatenate ALL chunks from 0 to get a valid WebM (needs header from chunk 0)
        all_data = b""
        for i in range(current_chunk_index):
            chunk_file = chunk_dir / f"chunk_{i:03d}.webm"
            if chunk_file.exists():
                all_data += chunk_file.read_bytes()

        if not all_data:
            return cumulative_offset

        # Convert full WebM to audio, then slice only the new portion
        full_audio = AudioSegment.from_file(io.BytesIO(all_data), format="webm")
        offset_ms = int(cumulative_offset * 1000)
        new_portion = full_audio[offset_ms:]

        if len(new_portion) == 0:
            return cumulative_offset

        new_duration_sec = len(new_portion) / 1000.0

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            new_portion.set_channels(1).set_frame_rate(16000).export(str(wav_path), format="wav")

            segments = transcribe(wav_path, language=language)

            for seg in segments:
                await websocket.send_json({
                    "type": "transcript",
                    "text": seg.text,
                    "start_time": seg.start_time + cumulative_offset,
                    "end_time": seg.end_time + cumulative_offset,
                })

                async with get_db() as db:
                    await db.execute(
                        "INSERT INTO transcript_segments (session_id, text, start_time, end_time) VALUES (?, ?, ?, ?)",
                        (session_id, seg.text, seg.start_time + cumulative_offset, seg.end_time + cumulative_offset),
                    )

            return cumulative_offset + new_duration_sec
        finally:
            if wav_path.exists():
                wav_path.unlink()
    except Exception:
        return cumulative_offset  # Don't crash the recording if transcription fails


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
        session_language = session.get("language", "en")

        # Update session status to recording
        await db.execute(
            "UPDATE sessions SET status = 'recording', updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )

    _active_recording_session = session_id

    # Prepare audio paths
    audio_dir = Path(f"data/audio/{campaign_id}")
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{session_id}.webm"

    # Disk-based chunk storage
    chunk_dir = audio_dir / f"tmp_{session_id}"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    chunk_count = 0
    cumulative_offset = 0.0
    transcription_in_progress = False

    try:
        while True:
            data = await websocket.receive()

            if "bytes" in data:
                # Write chunk to numbered file on disk
                chunk_file = chunk_dir / f"chunk_{chunk_count:03d}.webm"
                chunk_file.write_bytes(data["bytes"])
                chunk_count += 1

                # Run incremental transcription every ~10 chunks (skip if previous still running)
                if chunk_count % 10 == 0 and not transcription_in_progress:
                    current_chunk = chunk_count

                    async def _do_transcribe(ci: int, offset: float) -> None:
                        nonlocal cumulative_offset, transcription_in_progress
                        transcription_in_progress = True
                        try:
                            new_offset = await _run_transcription_on_chunk(
                                chunk_dir, ci, session_id, websocket, offset, session_language
                            )
                            cumulative_offset = new_offset
                        finally:
                            transcription_in_progress = False

                    asyncio.create_task(_do_transcribe(current_chunk, cumulative_offset))
            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "stop":
                    break
    except WebSocketDisconnect:
        pass
    finally:
        _active_recording_session = None

        # Merge chunk files into the final .webm
        chunk_files = sorted(chunk_dir.glob("chunk_*.webm"))
        if chunk_files:
            from talekeeper.services.audio import merge_chunk_files, webm_to_wav
            merge_chunk_files(chunk_dir, audio_path)

            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET audio_path = ?, status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (str(audio_path), session_id),
                )

            # Run speaker diarization on the final audio
            from talekeeper.services.diarization import run_final_diarization
            wav_path = webm_to_wav(audio_path)
            try:
                await run_final_diarization(session_id, wav_path)
            finally:
                if wav_path.exists():
                    wav_path.unlink()
        else:
            # No audio recorded, revert to draft and clean up
            if chunk_dir.exists():
                import shutil
                shutil.rmtree(chunk_dir)

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
