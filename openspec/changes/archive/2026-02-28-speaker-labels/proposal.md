# Speaker Labels

## Why

Transcript segments show no speaker identification — diarization runs but stores raw pyannote labels (SPEAKER_00) and the frontend only displays names when both character and player names are set. Speaker diarization is never triggered after recording or retranscription.

## What Changes

- Wire up `run_final_diarization()` to execute after recording stops and after retranscription completes
- Store friendly "Player N" labels instead of raw pyannote labels in the speakers table
- Update frontend speaker label display to show character name, player name, or diarization label (full fallback chain)
- Reload transcript after retranscription to pick up speaker-populated segments
- Clean up old speakers when retranscribing

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `speaker-diarization`: Diarization now triggers automatically and stores friendly labels

## Impact

- Backend: `diarization.py`, `recording.py`, `transcripts.py`
- Frontend: `TranscriptView.svelte`, `SpeakerPanel.svelte`
