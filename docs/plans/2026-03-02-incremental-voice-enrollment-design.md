# Incremental Voice Enrollment from Speaker Corrections

## Problem

Speaker diarization in unsupervised mode (no voice signatures) produces poor results:
speakers get merged together or split apart. The existing voice signature system works
but requires a separate explicit "generate signatures" step that users don't discover.

## Solution

Automatically enroll voice signatures when users assign speakers to roster entries
during transcript review. Each speaker correction teaches the system that player's voice.

## Workflow

1. User reviews transcript — speakers labeled "Player 1", "Player 2", etc.
2. User assigns "Player 1" → Alice / Gandalf via SpeakerPanel dropdown
3. Backend detects roster entry match → extracts embeddings from Player 1's segments
4. Voice signature created/updated for Alice in background (non-blocking)
5. Next session: diarization uses accumulated signatures, speakers come pre-labeled

## Design Decisions

### Trigger
- `PUT /api/speakers/{id}` endpoint, when updated player_name + character_name match a roster entry
- Runs as FastAPI `BackgroundTask` — response returns immediately

### Audio Sampling
- Sessions are 2-4 hours; processing all audio is wasteful
- Sample up to ~120 seconds of audio per speaker per enrollment
- Select segments longest-first (longer = cleaner embeddings, less boundary noise)
- Diminishing returns after ~2-3 minutes of speech per speaker verification research

### Signature Accumulation
- New roster entry (no existing signature): create fresh signature
- Existing signature: weighted average merge
  - `combined = (old_emb * old_count + new_emb * new_count) / total_count`
  - Re-L2-normalize
  - Update `num_samples`
- Reset: user can delete signature via existing `DELETE /api/voice-signatures/{id}`

## Changes Required

### Backend Service (`src/talekeeper/services/diarization.py`)
- New function `enroll_speaker_voice(session_id: int, speaker_id: int)`
  - Look up speaker's roster entry match
  - Load session audio, convert to WAV
  - Get speaker's transcript segments, sample up to ~120s (longest first)
  - Extract embedding via `extract_speaker_embedding()`
  - Create new signature or weighted-merge with existing
  - Log result, handle errors gracefully (no user-facing failures)

### Backend Router (`src/talekeeper/routers/speakers.py`)
- Modify `PUT /api/speakers/{id}` to accept `BackgroundTasks`
- After updating speaker fields, check if player_name + character_name match a roster entry
- If match found, schedule `enroll_speaker_voice` as background task

### No Changes Needed
- No frontend changes (existing SpeakerPanel already calls the right endpoint)
- No schema changes (`voice_signatures` table already has all needed fields)
- No new endpoints
