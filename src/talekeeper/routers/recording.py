"""WebSocket recording endpoint and audio management."""

import asyncio
import json
import mimetypes
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, Query, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from talekeeper.db import get_db
from talekeeper.paths import get_campaign_audio_dir

router = APIRouter(tags=["recording"])

# Track active recording session (in-process lock)
_active_recording_session: int | None = None


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

    # Prepare audio paths
    audio_dir = get_campaign_audio_dir(campaign_id)
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{session_id}.webm"

    # Disk-based chunk storage
    chunk_dir = audio_dir / f"tmp_{session_id}"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    chunk_count = 0
    num_speakers_override: int | None = None

    try:
        while True:
            data = await websocket.receive()

            if "bytes" in data:
                chunk_file = chunk_dir / f"chunk_{chunk_count:03d}.webm"
                chunk_file.write_bytes(data["bytes"])
                chunk_count += 1
            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "stop":
                    num_speakers_override = msg.get("num_speakers")
                    if num_speakers_override is not None:
                        num_speakers_override = int(num_speakers_override)
                        if not (1 <= num_speakers_override <= 10):
                            num_speakers_override = None
                    break
    except WebSocketDisconnect:
        pass
    finally:
        _active_recording_session = None

        # Merge chunk files into the final .webm
        chunk_files = sorted(chunk_dir.glob("chunk_*.webm"))
        if chunk_files:
            from talekeeper.services.audio import merge_chunk_files
            merge_chunk_files(chunk_dir, audio_path)

            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET audio_path = ?, status = 'audio_ready', updated_at = datetime('now') WHERE id = ?",
                    (str(audio_path.resolve()), session_id),
                )
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

    media_type = mimetypes.guess_type(str(audio_path))[0] or "application/octet-stream"

    return FileResponse(
        audio_path,
        media_type=media_type,
        headers={"Accept-Ranges": "bytes"},
    )


@router.post("/api/sessions/{session_id}/upload-audio")
async def upload_audio(session_id: int, file: UploadFile) -> dict:
    """Accept a multipart audio file upload for a session."""
    # Validate MIME type
    content_type = file.content_type or ""
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Only audio files are accepted")

    # Look up session
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, campaign_id, audio_path FROM sessions WHERE id = ?",
            (session_id,),
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")

    session = dict(rows[0])
    campaign_id = session["campaign_id"]

    # Derive extension from uploaded filename
    original_name = file.filename or ""
    ext = Path(original_name).suffix if "." in original_name else ""
    if not ext:
        # Fallback: guess from content type
        ext = mimetypes.guess_extension(content_type) or ""
    if not ext:
        ext = ".bin"

    # If session already has audio, delete old file and clear transcript/speakers
    old_audio_path = session.get("audio_path")
    if old_audio_path:
        old_path = Path(old_audio_path)
        if old_path.exists():
            old_path.unlink()
        async with get_db() as db:
            await db.execute(
                "DELETE FROM transcript_segments WHERE session_id = ?", (session_id,)
            )
            await db.execute(
                "DELETE FROM speakers WHERE session_id = ?", (session_id,)
            )

    # Save file to audio_dir/{campaign_id}/{session_id}.{ext}
    audio_dir = get_campaign_audio_dir(campaign_id)
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{session_id}{ext}"

    with open(audio_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)

    # Update session audio_path
    async with get_db() as db:
        await db.execute(
            "UPDATE sessions SET audio_path = ?, updated_at = datetime('now') WHERE id = ?",
            (str(audio_path), session_id),
        )

    return {"audio_path": str(audio_path)}


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/api/sessions/{session_id}/process-audio")
async def process_audio(session_id: int, num_speakers: int | None = Query(default=None, ge=1, le=10)) -> StreamingResponse:
    """Run transcription + diarization on uploaded audio, streaming progress via SSE."""
    from talekeeper.services.transcription import (
        transcribe_chunked,
        TranscriptSegment,
        ChunkProgress,
    )
    from talekeeper.services.resource_orchestration import (
        cleanup_transcription,
        cleanup_diarization,
    )

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")

        session = dict(rows[0])
        if not session.get("audio_path"):
            raise HTTPException(status_code=400, detail="No audio for this session")

        audio_path = Path(session["audio_path"])
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

        language = session.get("language", "en")

        model_rows = await db.execute_fetchall(
            "SELECT value FROM settings WHERE key = 'whisper_model'"
        )
        model_name = model_rows[0]["value"] if model_rows and model_rows[0]["value"] else None

    async def sse_generator() -> AsyncIterator[str]:
        segments_count = 0
        try:
            # Clear existing transcript/speakers and set status
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
            if model_name:
                kwargs["model_name"] = model_name
            for item in transcribe_chunked(audio_path, **kwargs):
                if isinstance(item, ChunkProgress):
                    yield _sse_event("progress", {
                        "chunk": item.chunk,
                        "total_chunks": item.total_chunks,
                    })
                elif isinstance(item, TranscriptSegment):
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

            cleanup_transcription()

            # Signal phase change to frontend
            yield _sse_event("phase", {"phase": "diarization"})

            # Run speaker diarization with progress reporting
            from talekeeper.services.diarization import run_final_diarization
            from talekeeper.services.audio import audio_to_wav

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
                await run_final_diarization(session_id, wav_path, num_speakers_override=num_speakers, progress_callback=_diarization_progress)
            finally:
                if wav_path.exists():
                    wav_path.unlink()

            for evt in progress_events:
                yield evt

            cleanup_diarization()

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
            yield _sse_event("error", {"message": str(exc)})
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.post("/api/sessions/{session_id}/process-all")
async def process_all(session_id: int, num_speakers: int | None = Query(default=None, ge=1, le=10)) -> StreamingResponse:
    """Run the full pipeline: transcription → diarization → summaries → image, with cleanup between phases."""
    from talekeeper.services.transcription import (
        transcribe_chunked,
        TranscriptSegment,
        ChunkProgress,
    )
    from talekeeper.services.resource_orchestration import (
        cleanup_transcription,
        cleanup_diarization,
        cleanup_llm,
        cleanup_image_generation,
    )

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")

        session = dict(rows[0])
        if not session.get("audio_path"):
            raise HTTPException(status_code=400, detail="No audio for this session")

        audio_path = Path(session["audio_path"])
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

        language = session.get("language", "en")

        model_rows = await db.execute_fetchall(
            "SELECT value FROM settings WHERE key = 'whisper_model'"
        )
        model_name = model_rows[0]["value"] if model_rows and model_rows[0]["value"] else None

    async def sse_generator() -> AsyncIterator[str]:
        segments_count = 0
        summaries_count = 0
        image_result = None

        try:
            # ---- Phase 1: Transcription ----
            yield _sse_event("phase", {"phase": "transcription"})

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
            if model_name:
                kwargs["model_name"] = model_name
            for item in transcribe_chunked(audio_path, **kwargs):
                if isinstance(item, ChunkProgress):
                    yield _sse_event("progress", {
                        "chunk": item.chunk,
                        "total_chunks": item.total_chunks,
                    })
                elif isinstance(item, TranscriptSegment):
                    async with get_db() as db:
                        await db.execute(
                            "INSERT INTO transcript_segments (session_id, text, start_time, end_time) VALUES (?, ?, ?, ?)",
                            (session_id, item.text, item.start_time, item.end_time),
                        )
                    segments_count += 1

            cleanup_transcription()

            # ---- Phase 2: Diarization ----
            yield _sse_event("phase", {"phase": "diarization"})

            from talekeeper.services.diarization import run_final_diarization
            from talekeeper.services.audio import audio_to_wav

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
                await run_final_diarization(session_id, wav_path, num_speakers_override=num_speakers, progress_callback=_diarization_progress)
            finally:
                if wav_path.exists():
                    wav_path.unlink()

            for evt in progress_events:
                yield evt

            cleanup_diarization()

            # Mark session completed after transcription + diarization
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

            # ---- Phase 3: Summaries ----
            yield _sse_event("phase", {"phase": "summaries"})

            from talekeeper.services import llm_client
            from talekeeper.services.summarization import (
                format_transcript,
                generate_full_summary,
                generate_pov_summary,
            )

            llm_config = await llm_client.resolve_config()
            base_url = llm_config["base_url"]
            api_key = llm_config["api_key"]
            llm_model = llm_config["model"]

            async with get_db() as db:
                segments = await db.execute_fetchall(
                    """SELECT ts.text, ts.start_time, ts.end_time,
                              sp.diarization_label, sp.player_name, sp.character_name
                       FROM transcript_segments ts
                       LEFT JOIN speakers sp ON sp.id = ts.speaker_id
                       WHERE ts.session_id = ?
                       ORDER BY ts.start_time""",
                    (session_id,),
                )

            if segments:
                transcript_text = format_transcript([dict(s) for s in segments])

                # Generate full summary
                full_content = await generate_full_summary(
                    transcript_text, base_url=base_url, api_key=api_key, model=llm_model,
                )
                async with get_db() as db:
                    await db.execute(
                        "INSERT INTO summaries (session_id, type, content, model_used) VALUES (?, 'full', ?, ?)",
                        (session_id, full_content, llm_model),
                    )
                summaries_count += 1

                # Generate POV summaries for named speakers
                async with get_db() as db:
                    speakers = await db.execute_fetchall(
                        "SELECT * FROM speakers WHERE session_id = ? AND character_name IS NOT NULL",
                        (session_id,),
                    )

                for speaker in speakers:
                    sp = dict(speaker)
                    pov_content = await generate_pov_summary(
                        transcript_text,
                        character_name=sp["character_name"],
                        base_url=base_url,
                        api_key=api_key,
                        model=llm_model,
                    )
                    async with get_db() as db:
                        await db.execute(
                            "INSERT INTO summaries (session_id, type, speaker_id, content, model_used) VALUES (?, 'pov', ?, ?, ?)",
                            (session_id, sp["id"], pov_content, llm_model),
                        )
                    summaries_count += 1

            await cleanup_llm(base_url, api_key, llm_model)

            # ---- Phase 4: Image Generation ----
            yield _sse_event("phase", {"phase": "image_generation"})

            from talekeeper.services.image_generation import (
                craft_scene_description,
                generate_session_image,
            )

            # Use the full summary for scene crafting if available
            scene_content = full_content if segments else None
            if scene_content:
                scene_desc = await craft_scene_description(
                    scene_content,
                    base_url=base_url,
                    api_key=api_key,
                    model=llm_model,
                    session_id=session_id,
                )
                image_result = await generate_session_image(
                    session_id, scene_desc, scene_desc,
                )

            cleanup_image_generation()

            # ---- Done ----
            yield _sse_event("done", {
                "segments_count": segments_count,
                "summaries_count": summaries_count,
                "image": image_result,
            })

            # Fire-and-forget: generate session name
            from talekeeper.services.session_naming import maybe_generate_and_update_name
            asyncio.create_task(maybe_generate_and_update_name(session_id))

        except Exception as exc:
            yield _sse_event("error", {"message": str(exc)})
            async with get_db() as db:
                await db.execute(
                    "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
