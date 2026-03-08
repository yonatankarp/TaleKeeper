## Why

Creating voice signatures currently requires a fully labeled session — the user must record a session, review the transcript, assign speakers, and then trigger "Generate Voice Signatures." This is a lot of upfront work before the system can identify anyone. Players who want accurate diarization from session 1 have no option to pre-enroll their voice. A simple audio upload on the party/roster screen lets users create a voice signature for each player in advance, before any session is recorded.

## What Changes

- Each roster entry on the Party screen gains an "Upload Voice Sample" button
- Clicking it opens a file picker accepting common audio formats (mp3, wav, m4a, ogg, etc.)
- The uploaded audio is converted to 16kHz mono WAV, run through VAD + WeSpeaker embedding extraction, and stored as a voice signature for that player
- The roster page shows whether each player already has a voice signature, and allows replacing it with a new upload
- If a voice signature already exists for that roster entry, it is replaced (same behaviour as the existing "Generate Voice Signatures" path)

## Capabilities

### Modified Capabilities
- `voice-signatures`: Add requirement for direct upload enrollment path — users can create a voice signature for a roster entry by uploading an audio sample, without needing a labeled session
- `speaker-diarization`: No change to diarization itself; the new signature is consumed by the existing diarization-with-signatures pipeline unchanged

## Impact

- **Backend router** (`src/talekeeper/routers/voice_signatures.py`): New endpoint `POST /api/roster/{entry_id}/upload-voice-sample` that accepts a multipart audio file, runs VAD + embedding extraction, and upserts the voice signature; new endpoint `GET /api/roster/{entry_id}/voice-signature` to check whether a signature exists
- **Backend service** (`src/talekeeper/services/diarization.py`): Reuses existing `extract_speaker_embedding`; no changes needed
- **Database**: No schema changes — uses existing `voice_signatures` table; `source_session_id` stored as NULL for directly uploaded samples
- **Frontend** (`frontend/src/routes/RosterPage.svelte`): Add voice signature status indicator and upload button per roster entry; load signature state on page load
- **Dependencies**: No new dependencies — reuses ffmpeg (via existing `audio_to_wav`) and WeSpeaker (via existing `extract_speaker_embedding`)
