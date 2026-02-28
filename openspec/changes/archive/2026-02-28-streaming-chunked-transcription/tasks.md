## 1. Audio service utilities

- [x] 1.1 Add `split_audio_to_chunks()` function to `services/audio.py` — takes a WebM/audio file path, chunk duration (default 5min), and overlap (default 30s); yields `(chunk_index, wav_path, start_ms, end_ms)` tuples, exporting each slice as a temp WAV (16kHz mono) and cleaning up after yield
- [x] 1.2 Add `merge_chunk_files()` function to `services/audio.py` — takes a directory of numbered `chunk_NNN.webm` files, concatenates them in order into a single `.webm` output file, then deletes the chunk directory
- [x] 1.3 Add `compute_primary_zone()` helper to `services/audio.py` — given chunk index, chunk start/end times, total chunks, and overlap duration, returns the `(zone_start, zone_end)` for midpoint-based deduplication

## 2. Chunked transcription service

- [x] 2.1 Add `transcribe_chunked()` generator to `services/transcription.py` — takes an audio file path, model size, and language; uses `split_audio_to_chunks()` to split the file, transcribes each chunk with `transcribe_stream()`, applies primary-zone deduplication, and yields `TranscriptSegment` objects with correct absolute timestamps
- [x] 2.2 Add `ChunkProgress` dataclass to `services/transcription.py` — holds `chunk` (1-based), `total_chunks`; yielded by `transcribe_chunked()` between chunks so callers can emit progress events

## 3. Disk-based recording (WebSocket handler)

- [x] 3.1 Rewrite `recording_ws()` in `routers/recording.py` to write each incoming binary chunk to a numbered file (`chunk_000.webm`, etc.) in `data/audio/<campaign_id>/tmp_<session_id>/` instead of appending to `list[bytes]`
- [x] 3.2 Update `_run_transcription_on_chunk()` to read only the new chunk files since the last transcription, concatenate their bytes, convert to WAV, transcribe, and offset-adjust timestamps using cumulative duration from prior chunks
- [x] 3.3 Update the `finally` block in `recording_ws()` to call `merge_chunk_files()` to produce the final `.webm`, then clean up the temp directory
- [x] 3.4 Add startup cleanup in app initialization to delete any orphaned `tmp_*` directories under `data/audio/`

## 4. SSE streaming retranscription endpoint

- [x] 4.1 Rewrite `retranscribe()` in `routers/transcripts.py` to return a `StreamingResponse` with `media_type="text/event-stream"` using an async generator
- [x] 4.2 Wire the async generator to use `transcribe_chunked()`, emitting `event: segment` for each segment, `event: progress` between chunks, and `event: done` on completion
- [x] 4.3 Persist each segment to `transcript_segments` table as it is emitted (before sending the SSE event)
- [x] 4.4 Delete existing transcript segments and set session status to `transcribing` at the start; set status to `completed` on done; handle errors with `event: error` and status recovery

## 5. Frontend SSE consumption

- [x] 5.1 Update the retranscribe call in the frontend to use `fetch` + `ReadableStream` to consume the SSE response, parsing `event:` and `data:` lines
- [x] 5.2 Append each received segment to the transcript list reactively as `segment` events arrive
- [x] 5.3 Add a progress indicator showing "Transcribing chunk N of M..." during retranscription
- [x] 5.4 Handle `done` event (remove progress indicator), `error` event (show error message, keep existing segments), and connection failures
