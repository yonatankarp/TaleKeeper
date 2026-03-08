## Context

Voice signatures are currently created in two ways:
1. **Batch**: `POST /api/sessions/{id}/generate-voice-signatures` — extracts embeddings from all labeled segments in a completed, fully-reviewed session.
2. **Incremental** (from `incremental-voice-enrollment` change): Auto-triggered in the background when a speaker is assigned to a roster entry during transcript review.

Both paths require a recorded session to exist first. There is no way to pre-enroll a player's voice before the first session. The Party/Roster screen already handles per-player file uploads (PDF character sheets) via `POST /api/roster/{entry_id}/upload-sheet`. This change follows the same pattern for audio.

The `extract_speaker_embedding(wav_path, time_ranges)` function in `diarization.py` already encapsulates the full pipeline: VAD → speaker change detection → WeSpeaker embedding extraction → averaging + L2-normalization. Passing the full audio duration as a single time range reuses this without modification.

`audio_to_wav()` in `services/audio.py` converts any pydub-supported format to 16kHz mono WAV. The pattern of accepting an audio file, writing to a temp file, converting, processing, and cleaning up is established in the recording and re-diarization paths.

Blocking CPU work (embedding extraction) is offloaded to a thread via `asyncio.to_thread()`, matching the pattern used elsewhere in `app.py`.

## Goals / Non-Goals

**Goals:**
- Allow uploading an audio sample for any roster entry to create or replace its voice signature
- Show per-player voice signature status (has/none) on the Party screen
- Run embedding extraction off the event loop so the route handler stays non-blocking
- Reuse all existing infrastructure — no new ML models, no new dependencies

**Non-Goals:**
- Merging with existing signatures (uploads replace, not merge — the user is intentionally providing a clean reference sample)
- Audio quality validation or speaker count detection in the uploaded sample
- Progress feedback during extraction (short samples process in seconds; long samples are the user's choice)
- Storing the raw audio sample (only the embedding is persisted)
- Accepting URLs instead of file uploads

## Decisions

### Decision 1: Replace (not merge) on upload

When a voice signature already exists for a roster entry, uploading a new sample replaces it entirely (DELETE + INSERT), identical to the behaviour of `generate-voice-signatures`.

**Why:** An uploaded voice sample is a deliberate, clean reference recording — unlike incremental enrollment from a noisy session, it should be treated as authoritative. Merging would dilute a high-quality recording with earlier lower-quality data.

**Alternative considered:** Weighted merge (as used in incremental enrollment). Rejected because the intent of an upload is "use this as the reference," not "add this to existing knowledge."

### Decision 2: Single GET endpoint for signature status, not embedded in roster list

A dedicated `GET /api/roster/{entry_id}/voice-signature` endpoint returns the signature metadata (id, num_samples, created_at) or 404 if none exists. The frontend fetches this per-entry on page load.

**Why:** The existing `GET /api/campaigns/{campaign_id}/voice-signatures` endpoint already returns all signatures for a campaign with roster_entry_id. The frontend can use that single call to determine status for all entries efficiently, without N+1 per-entry requests.

**Revised approach:** Load all voice signatures for the campaign once via the existing endpoint, then index by roster_entry_id in the frontend. No new GET endpoint needed.

### Decision 3: asyncio.to_thread for blocking extraction

The upload endpoint writes the file, converts it, then calls `asyncio.to_thread(extract_speaker_embedding, wav_path, [...])` before returning the response.

**Why:** `extract_speaker_embedding` runs VAD and WeSpeaker inference — both are CPU-bound and blocking. The app uses `asyncio.to_thread()` as its established pattern for offloading blocking operations (used in `app.py`). The upload blocks until extraction completes so the response can include the result (success/failure). A voice sample upload is an explicit user action that warrants a loading state, unlike background incremental enrollment.

**Alternative considered:** BackgroundTask (fire-and-forget). Rejected because the user needs immediate confirmation that their sample produced a valid voice signature. Without a response, they have no way to know if the upload worked.

### Decision 4: Accept any audio format; cap input at 2 minutes

The endpoint accepts any `UploadFile` (no MIME restriction in the API; pydub handles format detection). Audio longer than 2 minutes is truncated to the first 2 minutes before extraction.

**Why:** A voice sample upload is a deliberate short recording — 30-60 seconds is the typical and ideal length. 2 minutes provides a generous ceiling while keeping extraction fast (under 5 seconds on typical hardware). Restricting MIME types is error-prone (browser-reported types vary); pydub's `AudioSegment.from_file` reliably detects format from the file content.

**Alternative considered:** File size limit (e.g., 50MB). Rejected because size varies by codec; time-based truncation is semantically meaningful and codec-agnostic.

### Decision 5: NULL source_session_id for uploaded samples

The `voice_signatures` table has `source_session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL`. Uploaded samples store NULL, matching the schema's existing provision for signatures not tied to a session.

**Why:** The column is already nullable for exactly this case. No migration needed.

## Risks / Trade-offs

**[Risk] Low-quality uploaded audio produces a noisy signature** → User's responsibility. The replace-on-upload semantics mean they can re-upload a better sample at any time.

**[Risk] Thread executor saturation during concurrent uploads** → Single-user local app; concurrent uploads are not a realistic scenario. asyncio.to_thread uses the default ThreadPoolExecutor which has sufficient capacity.

**[Trade-off] No streaming progress during extraction** → Extraction of a 2-minute sample may take 2-5 seconds on slower hardware. The frontend shows a loading spinner on the button. A future enhancement could use SSE for extraction progress, but it's disproportionate complexity for an infrequent one-time action.

**[Trade-off] Uploaded audio is not stored** → Only the embedding is persisted. If the user wants to re-generate, they must re-upload. This is intentional — storing raw audio indefinitely raises storage concerns and is not needed for the use case.
