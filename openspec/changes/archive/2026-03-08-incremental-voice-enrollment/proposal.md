## Why

Speaker diarization in unsupervised mode produces poor results — speakers get merged together or split apart. The existing voice signature system solves this, but requires users to manually label an entire session and then trigger a separate "Generate Voice Signatures" action. This workflow is undiscoverable and cumbersome. Users should be able to teach the system who each player is simply by correcting speaker assignments during normal transcript review, with the system learning incrementally in the background.

## What Changes

- When a user assigns a speaker to a roster entry (via the existing speaker update endpoint), the system automatically extracts voice embeddings from that speaker's transcript segments and creates or updates the corresponding voice signature
- Audio sampling is capped at ~120 seconds per enrollment (longest segments first) to keep the operation fast even for 2-4 hour sessions
- New enrollments are weighted-merged with existing signatures so knowledge accumulates across sessions without overwriting previous data
- Enrollment runs as a non-blocking background task — the speaker update response returns immediately

## Capabilities

### New Capabilities
- `incremental-voice-enrollment`: Automatic voice signature enrollment triggered by speaker-to-roster assignment during transcript review, with audio sampling cap and weighted merge accumulation

### Modified Capabilities
- `voice-signatures`: Add requirement for incremental enrollment path (current spec only covers batch extraction from fully labeled sessions) and weighted merge accumulation strategy

## Impact

- **Backend service** (`src/talekeeper/services/diarization.py`): New `enroll_speaker_voice` async function handling audio sampling, embedding extraction, and signature create/merge
- **Backend router** (`src/talekeeper/routers/speakers.py`): `PUT /api/speakers/{id}` gains BackgroundTasks integration to trigger enrollment when roster match detected
- **Database**: No schema changes — uses existing `voice_signatures` table
- **Frontend**: No changes — existing SpeakerPanel dropdown already calls the right endpoint
- **Dependencies**: No new dependencies — reuses existing SpeechBrain ECAPA-TDNN encoder
