## 1. Backend endpoint

- [x] 1.1 Add `ReDiarizeRequest` Pydantic model in `routers/speakers.py` with required `num_speakers: int` field (ge=1, le=10)
- [x] 1.2 Add `POST /api/sessions/{session_id}/re-diarize` endpoint in `routers/speakers.py` returning `StreamingResponse` with `text/event-stream`
- [x] 1.3 Add session validation: return 404 if session not found, 400 if no audio file, 409 if status is not `completed`
- [x] 1.4 Implement SSE generator: emit `phase` event, run cleanup + diarization + done/error events, with session status lifecycle (`diarizing` → `completed`)

## 2. Speaker data cleanup

- [x] 2.1 In the SSE generator, before diarization: set `speaker_id = NULL` on all `transcript_segments` for the session
- [x] 2.2 Delete voice signatures where `source_session_id` matches the session
- [x] 2.3 Delete all speaker rows for the session

## 3. Diarization and WAV handling

- [x] 3.1 Convert audio to WAV using `audio_to_wav`, call `run_final_diarization(session_id, wav_path, num_speakers_override=num_speakers)`
- [x] 3.2 Clean up temporary WAV file in a `finally` block
- [x] 3.3 On success: emit `done` event with `segments_count` (count of transcript segments for the session); on error: emit `error` event and restore status to `completed`

## 4. Frontend UI

- [x] 4.1 Add `reDiarize()` function in `TranscriptView.svelte` that POSTs to `/api/sessions/{session_id}/re-diarize` with `{ num_speakers: retranscribeNumSpeakers }` and consumes the SSE stream
- [x] 4.2 Add a "Re-diarize" button in the `.retranscribe-bar` next to the "Retranscribe" button, disabled during transcribing/diarizing, sharing the existing speaker count input
- [x] 4.3 Add confirmation dialog before triggering re-diarization warning that speaker assignments and session voice signatures will be lost
- [x] 4.4 Handle SSE events: show diarization progress, refresh transcript and speaker panel on `done`, show error on `error`
- [x] 4.5 Update the retranscribe bar visibility condition to also hide/disable during `diarizing` status

## 5. Frontend API integration

- [x] 5.1 Add `reDiarize(sessionId: number, numSpeakers: number)` function in `api.ts` if needed, or use raw `fetch` (matching the retranscribe pattern)
