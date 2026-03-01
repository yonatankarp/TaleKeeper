## Why

After transcribing a session, the speaker clustering (diarization) may produce incorrect speaker groupings — for example, merging two speakers into one or splitting one speaker into two. Currently, the only way to fix this is to retranscribe the entire session, which is slow and wasteful since the transcript text itself is fine. Users need a way to re-run just the diarization step with a different speaker count, keeping the existing transcript segments intact.

## What Changes

- Add a new backend endpoint that re-runs diarization on an already-transcribed session without re-running Whisper transcription
- The endpoint deletes existing speakers and their voice signatures for the session, then re-runs `run_final_diarization` using the session's stored audio and the caller-supplied `num_speakers` value
- Existing transcript segments (text + timestamps) are preserved; only `speaker_id` assignments are updated
- Uses campaign voice signatures for speaker matching when available (same behavior as initial diarization)
- Add a "Re-diarize" button in the retranscribe bar (next to the existing "Retranscribe" button) that lets the user pick a speaker count and trigger re-diarization
- The frontend streams diarization progress via SSE and refreshes the speaker panel + transcript on completion

## Capabilities

### New Capabilities
- `session-re-diarization`: Re-run speaker diarization on a completed session without re-transcribing, including the backend endpoint, cleanup of old speakers/signatures, and frontend trigger with progress feedback

### Modified Capabilities
_(none — existing speaker-diarization and voice-signatures specs are unaffected; this is an additive capability that reuses the existing diarization pipeline)_

## Impact

- **Backend**: New endpoint in `routers/speakers.py` or `routers/recording.py`; reuses existing `run_final_diarization` from `services/diarization.py`
- **Database**: Deletes and recreates rows in `speakers` and `voice_signatures` tables for the target session; `transcript_segments.speaker_id` is updated in-place
- **Frontend**: New button + SSE handler in `TranscriptView.svelte`; `SpeakerPanel` re-fetches after completion
- **No new dependencies**: Reuses existing diarization, embedding extraction, and clustering code
