## ADDED Requirements

### Requirement: Re-diarization respects campaign source separation setting
The re-diarize endpoint SHALL read the session's campaign `source_separation_enabled` flag and apply the same separation stage as initial diarization when the flag is set. The SSE event contract for re-diarization SHALL include the new `separation_start`, `separation_done`, and `separation_error` stage events when separation runs.

#### Scenario: Re-diarize with separation enabled
- **WHEN** a POST request is made to `/api/sessions/{session_id}/re-diarize` for a session in a campaign with `source_separation_enabled = true`
- **THEN** the re-diarization pipeline runs source separation before VAD, emitting `separation_start` and `separation_done` SSE progress events

#### Scenario: Re-diarize with separation disabled
- **WHEN** a POST request is made to `/api/sessions/{session_id}/re-diarize` for a session in a campaign with `source_separation_enabled = false`
- **THEN** the re-diarization pipeline runs without separation, identical to current behaviour

#### Scenario: Separation failure during re-diarization falls back gracefully
- **WHEN** source separation raises an exception during re-diarization
- **THEN** a `separation_error` SSE progress event is emitted and re-diarization continues on the original audio without aborting
