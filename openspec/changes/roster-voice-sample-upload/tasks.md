# Tasks: roster-voice-sample-upload

## Group 1: Backend — Upload endpoint

- [ ] 1.1 Add `POST /api/roster/{entry_id}/upload-voice-sample` to `src/talekeeper/routers/voice_signatures.py`
  - Accept `UploadFile`
  - Verify the roster entry exists; return 404 if not; read the campaign_id from the entry
  - Write upload bytes to a temp file, run `audio_to_wav` (truncating to 2 minutes via pydub before writing the WAV), clean up temp files in a `finally` block
  - Call `asyncio.to_thread(extract_speaker_embedding, wav_path, [(0.0, 120.0)])` to stay non-blocking
  - Return 400 with `"No speech detected in uploaded audio"` if embedding is None
  - DELETE existing signature for this roster entry, INSERT new one with `source_session_id=NULL`
  - Return `{id, roster_entry_id, campaign_id, num_samples, created_at}`

## Group 2: Backend — Tests

- [ ] 2.1 Add tests to `tests/integration/routers/test_voice_signatures.py`:
  - `test_upload_voice_sample_creates_signature` — mock `extract_speaker_embedding` to return a fake embedding; assert 200 and signature in DB
  - `test_upload_voice_sample_replaces_existing` — seed an existing signature; upload a new sample; assert only one signature remains
  - `test_upload_voice_sample_no_speech_returns_400` — mock `extract_speaker_embedding` to return None; assert 400
  - `test_upload_voice_sample_roster_not_found` — use nonexistent entry_id; assert 404

## Group 3: Frontend — Party screen

- [ ] 3.1 In `frontend/src/routes/RosterPage.svelte`, load voice signatures for the campaign on page load alongside roster entries:
  - Fetch `GET /api/campaigns/{campaignId}/voice-signatures` in `load()`
  - Build a `Map<number, VoiceSig>` keyed by `roster_entry_id` (`$state`)

- [ ] 3.2 Add "Upload Voice Sample" button per roster entry (in the `btn-group` alongside existing buttons):
  - Clicking calls a `triggerVoiceUpload(entryId)` function that opens a file picker (`accept="audio/*"`)
  - On file selection, POST to `/api/roster/{entryId}/upload-voice-sample` as `multipart/form-data` with field `file`
  - Track loading state with `voiceUploadingId` ($state); disable button while uploading; show spinner
  - On success, refresh voice signatures map; on error, set `uploadError`

- [ ] 3.3 Show voice signature status badge per roster entry:
  - If the entry has a signature in the map: show a small "Voice signature" badge (reuse `inactive-badge` style variant or add a new `sig-badge` class)
  - If no signature: no badge (upload button alone is the affordance)
