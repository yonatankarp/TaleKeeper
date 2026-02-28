## Context

TaleKeeper records D&D sessions via browser WebRTC audio, streams chunks over a WebSocket, and transcribes them with faster-whisper running locally. Two transcription paths exist:

1. **Live recording** (`/ws/recording/{session_id}`): Accumulates all WebM chunks in an in-memory `list[bytes]`. Every 10 chunks (~10s), re-transcribes the entire accumulated buffer from the start, filtering by offset. On stop, writes all chunks to a single `.webm` file.

2. **Retranscription** (`POST /api/sessions/{session_id}/retranscribe`): Converts the full stored `.webm` to WAV in one shot, runs `transcribe()` blocking, returns only when complete.

Both paths have unbounded memory growth and get progressively slower for long recordings (3-4+ hours). The retranscribe path will also HTTP timeout on large files.

A `transcribe_stream()` generator already exists in `services/transcription.py` but is unused.

## Goals / Non-Goals

**Goals:**
- Bounded memory: recording and retranscription use constant memory regardless of session length
- Incremental live transcription: only transcribe new audio, not re-process everything from the start
- Streaming retranscription: return results progressively via SSE instead of blocking
- Chunked processing: split large audio files into manageable pieces for retranscription
- Final merged file: recording still produces a single `.webm` file at `data/audio/<campaign_id>/<session_id>.webm`

**Non-Goals:**
- Parallel chunk transcription (Whisper model is a singleton; concurrent calls would serialize anyway)
- Changing the audio format or codec (WebM/Opus stays as-is)
- Real-time word-level streaming (faster-whisper produces segment-level output)
- Modifying the speaker diarization pipeline

## Decisions

### 1. Disk-based chunk accumulation during live recording

**Decision:** Write each incoming WebSocket chunk to a numbered file on disk (`chunk_000.webm`, `chunk_001.webm`, ...) in a temporary directory under `data/audio/<campaign_id>/tmp_<session_id>/`. On recording stop, concatenate all chunk files into the final `.webm` and delete the temp directory.

**Why not append to a single file?** WebM containers have header metadata. Each browser MediaRecorder chunk is a self-contained WebM segment. Concatenating raw bytes works (the current code already does this), but individual files let us convert only the latest chunk for incremental transcription without re-reading everything.

**Alternatives considered:**
- *Memory-mapped file*: Adds complexity, still need the full file in virtual memory.
- *Streaming write to single file + seek*: WebM isn't easily seekable for extracting the latest N seconds.

### 2. Incremental-only live transcription

**Decision:** When the transcription interval fires (every 10 chunks), convert only the latest batch of chunks (since last transcription) to WAV and transcribe that slice. Use a running time offset to set correct timestamps on the resulting segments.

The offset is calculated from the duration of all previously transcribed chunks. After converting the new chunk batch to WAV, measure the WAV duration via `pydub` to advance the offset for the next cycle.

**Why not keep re-transcribing everything?** A 3-hour recording would mean converting and transcribing 3 hours of audio every 10 seconds. This is the core scalability problem.

**Trade-off:** Chunk boundaries may split words. faster-whisper's VAD filter handles silence, but mid-word splits at chunk edges can produce artifacts. This is acceptable for live preview — the retranscribe path with overlapping chunks produces the clean final transcript.

### 3. Overlapping chunks for retranscription

**Decision:** Split the stored audio file into segments of 5 minutes with 30-second overlap on each side. Each chunk is converted to WAV independently and transcribed. Segments from overlapping regions are deduplicated by preferring the segment from the chunk where it falls in the interior (not near an edge).

**Chunk splitting approach:** Use `pydub.AudioSegment` to load the full audio, slice by millisecond offsets, and export each slice as a temporary WAV. Only one slice is held in memory at a time — load, export, release.

**Deduplication strategy:** For each chunk, only keep segments whose midpoint falls within the chunk's "primary zone" (the non-overlapping interior). This means:
- Chunk 0 (0:00–5:00): keep segments with midpoint in 0:00–4:45
- Chunk 1 (4:30–9:30): keep segments with midpoint in 4:45–9:15
- Chunk 2 (9:00–14:00): keep segments with midpoint in 9:15–13:45
- Last chunk: keep all remaining segments

**Alternatives considered:**
- *No overlap*: Risks losing words at boundaries.
- *1-minute overlap*: Wastes transcription time; 30s is sufficient for faster-whisper's context window.
- *Dedup by text similarity*: Fragile and complex. Midpoint-based zone assignment is deterministic and simple.

### 4. SSE for streaming retranscription

**Decision:** Change `POST /api/sessions/{session_id}/retranscribe` to return a `StreamingResponse` with `text/event-stream` content type. Each transcript segment is sent as an SSE event as it's produced. The frontend consumes this with `EventSource` or `fetch` + `ReadableStream`.

SSE event format:
```
event: segment
data: {"text": "...", "start_time": 0.0, "end_time": 2.5}

event: progress
data: {"chunk": 2, "total_chunks": 12}

event: done
data: {"segments_count": 156}
```

The endpoint processes chunks sequentially: split → convert chunk to WAV → transcribe chunk (streaming segments) → emit SSE events → move to next chunk. This keeps only one WAV chunk in memory at a time.

**Why SSE over WebSocket?** Retranscription is a unidirectional server-to-client stream. SSE is simpler, uses standard HTTP, and needs no connection upgrade. The recording path already uses WebSocket (bidirectional), so both patterns coexist naturally.

**Alternatives considered:**
- *WebSocket*: Overkill for unidirectional streaming; adds client-side complexity.
- *Polling*: Requires storing intermediate state; higher latency.

### 5. Frontend SSE consumption

**Decision:** Use the `fetch` API with `ReadableStream` rather than `EventSource`. `EventSource` only supports GET requests; retranscribe needs POST with a request body. The frontend will:
1. Send `POST /retranscribe` with `Accept: text/event-stream`
2. Read the response body as a stream, parsing SSE lines
3. Append each segment to the transcript list reactively
4. Show a progress indicator (chunk N of M)

### 6. Temporary file cleanup

**Decision:** All temporary files (chunk WAVs, split audio segments) are created in the system temp directory via `tempfile` and cleaned up in `finally` blocks. The chunk directory during recording (`data/audio/<campaign_id>/tmp_<session_id>/`) is cleaned up when the final `.webm` is assembled. If the process crashes mid-recording, orphaned chunk directories can be cleaned up on next startup.

## Risks / Trade-offs

- **Chunk boundary artifacts in live transcription** → Acceptable for live preview; retranscribe produces clean output. Could add a small overlap in future if needed.
- **Disk I/O during recording** → Writing 1KB chunks every second is negligible. SSDs handle this trivially.
- **pydub loading full file for splitting** → `pydub.AudioSegment.from_file()` loads the entire file into memory. For a 4-hour WebM at ~40MB, this is fine. For truly huge files, could use `ffmpeg` CLI directly with `-ss`/`-t` flags to extract slices without loading the full file. Defer this optimization.
- **Single-threaded Whisper** → Chunks are processed sequentially. This is inherent to the singleton model design. Not a regression from current behavior.
- **Orphaned temp directories on crash** → Add a startup cleanup sweep for `tmp_*` directories under `data/audio/`. Low priority since crashes during recording are rare.
