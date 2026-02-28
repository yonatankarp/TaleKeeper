## Why

Recording sessions can be 3-4+ hours long. The current implementation accumulates all audio chunks in memory during recording, re-transcribes the entire accumulated buffer every ~10 seconds, and retranscription blocks until the full file is processed. This causes unbounded memory growth, progressively slower transcription cycles, and HTTP timeouts on long recordings.

## What Changes

- **Disk-based chunk storage during recording**: Write incoming WebSocket audio chunks directly to disk instead of accumulating in an in-memory `list[bytes]`. Merge chunks into a single `.webm` file when recording stops.
- **Incremental-only transcription during recording**: Transcribe only the latest chunk (not the full accumulated buffer) and use time offsets to stitch segments together.
- **Chunked retranscription for stored files**: Split large audio files into overlapping segments (e.g., 5-minute windows with 30-second overlap), transcribe each independently, and deduplicate overlapping transcript segments.
- **SSE streaming for retranscription results**: Replace the blocking `POST /retranscribe` endpoint with an SSE (Server-Sent Events) response that streams transcript segments to the frontend as Whisper produces them, using the existing `transcribe_stream()` generator.
- **Bounded memory usage**: Memory consumption during both recording and retranscription becomes constant regardless of session length.

## Capabilities

### New Capabilities

- `chunked-audio-processing`: Disk-based chunk storage during recording, chunk merging on stop, and splitting large stored files into overlapping segments for transcription.
- `streaming-retranscription`: SSE-based retranscription endpoint that streams transcript segments to the frontend as they are produced, with frontend UI updates for progressive results.

### Modified Capabilities

None (no existing specs).

## Impact

- **Backend routers**: `recording.py` (WebSocket handler rewrite for disk-based chunks), `sessions.py` (retranscribe endpoint changed to SSE)
- **Backend services**: `transcription.py` (chunked transcription logic, wire up `transcribe_stream()`), `audio.py` (chunk merge utility, audio splitting utility)
- **Frontend**: `TranscriptView.svelte` or retranscribe UI (consume SSE stream, show progressive results)
- **Disk I/O**: New temporary chunk files under `data/audio/` during recording (cleaned up on merge)
- **No new dependencies**: `faster-whisper`, `pydub`, and `aiosqlite` already support all needed operations. SSE uses standard HTTP streaming (no new library needed with FastAPI's `StreamingResponse`).
