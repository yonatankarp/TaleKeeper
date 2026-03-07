## ADDED Requirements

### Requirement: Pre-diarization audio source separation
When source separation is enabled for a campaign, the system SHALL decompose the single-channel session audio into 2 separated speaker streams using SpeechBrain SepFormer before diarization begins. Separation MUST run on the full audio file (chunked internally to bound memory usage) and produce 2 temporary WAV files. Both streams SHALL be fed into the VAD and embedding extraction stages alongside or in place of the original mixed audio. Temporary stream files MUST be deleted in a `finally` block after diarization completes, regardless of success or failure.

#### Scenario: Separation runs before VAD when enabled
- **WHEN** diarization is triggered for a session in a campaign with `source_separation_enabled = true`
- **THEN** SepFormer runs on the session audio and produces 2 separated stream files before VAD begins

#### Scenario: Separation skipped when disabled
- **WHEN** diarization is triggered for a session in a campaign with `source_separation_enabled = false`
- **THEN** the pipeline runs exactly as before with no separation stage

#### Scenario: Separated streams cleaned up on success
- **WHEN** diarization completes successfully after separation
- **THEN** both temporary stream WAV files are deleted

#### Scenario: Separated streams cleaned up on error
- **WHEN** an error occurs during diarization after separation has run
- **THEN** both temporary stream WAV files are still deleted

### Requirement: SpeechBrain SepFormer model download and caching
The system SHALL download the SepFormer model (`speechbrain/sepformer-wsj02mix`) from HuggingFace on first use and cache it locally under `~/.cache/speechbrain/`. Subsequent runs MUST use the cached model without requiring internet access. The download MUST surface a progress SSE event so the frontend can inform the DM.

#### Scenario: First-run model download
- **WHEN** source separation is triggered for the first time and no local model cache exists
- **THEN** the system downloads the SepFormer model (~200MB) and emits a `separation_downloading` SSE progress event during the download

#### Scenario: Cached model used on subsequent runs
- **WHEN** source separation is triggered and the model is already cached locally
- **THEN** the model is loaded from cache with no network request

### Requirement: Separation failure fallback
If the separation stage raises an exception (network failure during model download, out of memory, or model inference error), the system SHALL log the error, emit a `separation_error` SSE progress event with the error message, and continue diarization on the original unseparated audio without aborting the session.

#### Scenario: Separation fails gracefully
- **WHEN** SepFormer inference raises an exception (e.g., out of memory)
- **THEN** a `separation_error` SSE progress event is emitted, diarization continues on the original audio, and the session is not aborted

### Requirement: SSE progress events for separation stage
The diarization SSE event vocabulary SHALL include two new stage events: `separation_start` (emitted before SepFormer inference begins) and `separation_done` (emitted after both stream files are written). These events SHALL follow the same `event: progress` structure as existing diarization stage events.

#### Scenario: Separation start event emitted
- **WHEN** source separation begins
- **THEN** an `event: progress` SSE event is emitted with stage `separation_start`

#### Scenario: Separation done event emitted
- **WHEN** source separation completes and stream files are ready
- **THEN** an `event: progress` SSE event is emitted with stage `separation_done`
