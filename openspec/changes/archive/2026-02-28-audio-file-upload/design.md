## Context

TaleKeeper currently ingests audio only via live WebSocket recording from the browser microphone. The audio is saved as `.webm` and the session transitions through `draft → recording → completed`. Transcription happens incrementally during recording (every 10 chunks) and can be re-run via the retranscribe endpoint which uses `transcribe_chunked` with SSE progress streaming. Speaker diarization runs on the final audio after recording stops.

Users want to import audio recorded on external devices (e.g., iPhone voice memos, typically `.m4a`). A 4-hour session recording is a realistic use case, so memory efficiency matters.

## Goals / Non-Goals

**Goals:**
- Allow uploading audio files from external devices to a session
- Support common audio formats (m4a, mp3, wav, webm, ogg, flac)
- Run the full pipeline (transcription + diarization) automatically after upload
- Show progress during both upload and transcription phases
- Allow re-uploading to replace existing audio

**Non-Goals:**
- Drag-and-drop upload (standard file picker is sufficient)
- Batch upload of multiple files
- Audio format validation beyond what pydub/ffmpeg can handle
- Editing or trimming uploaded audio

## Decisions

### Store uploaded files in original format
**Decision:** Save the uploaded file as-is (e.g., `.m4a`) rather than converting to `.webm` first.

**Rationale:** Converting a 4-hour file to webm would be slow and use significant disk space for a redundant copy. pydub/ffmpeg in `split_audio_to_chunks` already reads any format that ffmpeg supports. The `audio_path` DB column stores the full path including extension, so no schema change needed.

**Alternative considered:** Convert to webm on upload for consistency. Rejected because it adds latency and disk usage with no benefit — the transcription pipeline doesn't care about the container format.

### Two-endpoint approach: upload then process
**Decision:** Split into `POST /api/sessions/{id}/upload-audio` (multipart file upload) and `POST /api/sessions/{id}/process-audio` (SSE transcription stream).

**Rationale:** The upload itself may take significant time for large files. Separating upload from processing lets the frontend show distinct progress phases (uploading vs transcribing). The process endpoint reuses the same SSE pattern as the existing `retranscribe` endpoint.

**Alternative considered:** Single endpoint that accepts the upload and streams back transcription progress. Rejected because FastAPI can't easily stream SSE responses while simultaneously consuming a large multipart upload in the same request.

### Upload replaces existing audio
**Decision:** Uploading to a session with existing audio deletes the old audio file, clears transcript segments and speakers, and starts fresh.

**Rationale:** This matches the user's mental model — they're providing the audio for this session. Keeping both would require a more complex UI for selecting which audio to use. The retranscribe endpoint already follows this replace pattern.

### File extension from uploaded filename
**Decision:** Derive the saved file's extension from the uploaded filename (e.g., `session_3.m4a`), falling back to the content type if no extension is present.

**Rationale:** The original extension is the most reliable indicator of format for ffmpeg. Content-type headers from browsers can be generic (e.g., `application/octet-stream`).

## Risks / Trade-offs

- **Large file upload timeout** → FastAPI streams multipart uploads by default via `UploadFile`, so memory stays bounded. The frontend should not set a short fetch timeout for the upload request.
- **Unsupported audio format** → If ffmpeg can't decode the file, `transcribe_chunked` will fail. The SSE error event will surface this to the user. No pre-validation needed since ffmpeg supports virtually all common formats.
- **Audio playback in browser** → The browser's `<audio>` element may not support all formats (e.g., `.flac`). The existing `AudioPlayer` serves the file as-is. If playback fails, the user still gets their transcript — playback is a nice-to-have. The content type for the audio endpoint should be derived from the file extension.
