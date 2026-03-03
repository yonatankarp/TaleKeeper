# Session Pipeline

## Purpose

Provide a one-click "Process All" capability that runs the full session processing pipeline (transcription, diarization, summaries, session art) sequentially with memory cleanup between phases, alongside the existing individual phase triggers.

## ADDED Requirements

### Requirement: Full session processing pipeline endpoint
The system SHALL provide a `POST /api/sessions/{session_id}/process-all` SSE endpoint that runs the complete session processing pipeline sequentially: transcription, diarization, summary generation (full + POV), and image generation. Memory cleanup SHALL run between each phase. The endpoint SHALL accept an optional `num_speakers` query parameter.

#### Scenario: Process all phases sequentially
- **WHEN** the DM triggers "Process All" on a session with audio
- **THEN** the system runs transcription, then diarization, then summary generation, then image generation in sequence, with memory cleanup between each phase

#### Scenario: Pipeline requires audio
- **WHEN** the DM triggers "Process All" on a session without audio
- **THEN** the system returns HTTP 400 with an error explaining that audio is required

#### Scenario: Individual phase triggers remain available
- **WHEN** the DM prefers to run phases manually
- **THEN** the existing endpoints (process-audio, generate summary, generate image) continue to work independently

### Requirement: Pipeline SSE progress reporting
The system SHALL emit SSE events throughout the pipeline indicating the current phase, progress within each phase, and completion. The event format SHALL be compatible with the existing SSE consumption pattern in the frontend.

#### Scenario: Phase transition events
- **WHEN** the pipeline transitions from transcription to diarization
- **THEN** an `event: phase` SSE event is emitted with `{"phase": "diarization"}`

#### Scenario: Transcription progress within pipeline
- **WHEN** chunked transcription is running as part of the pipeline
- **THEN** `event: progress` SSE events are emitted with chunk progress (same format as process-audio)

#### Scenario: Pipeline completion
- **WHEN** all four phases complete successfully
- **THEN** an `event: done` SSE event is emitted with a summary of what was generated (segment count, summary count, image metadata)

### Requirement: Pipeline error handling
The system SHALL stop the pipeline if any phase fails, report the error via SSE, and leave the session in a consistent state. Phases that completed before the failure SHALL have their results preserved.

#### Scenario: Phase failure stops pipeline
- **WHEN** diarization fails during the pipeline
- **THEN** the pipeline stops, an `event: error` SSE event is emitted with the error details, and the transcription results from the previous phase are preserved in the database

#### Scenario: Session status after pipeline failure
- **WHEN** a pipeline phase fails
- **THEN** the session status is set to `completed` (not left in an intermediate state like `transcribing`)

### Requirement: Process All UI button
The system SHALL display a "Process All" button on the session page when the session has audio and is not currently being processed. The button SHALL show a multi-phase progress indicator during pipeline execution.

#### Scenario: Button visibility
- **WHEN** a session has audio and is in `audio_ready` or `completed` status
- **THEN** a "Process All" button is displayed alongside the existing individual action buttons

#### Scenario: Multi-phase progress display
- **WHEN** the pipeline is running
- **THEN** the UI shows which phase is currently executing (e.g., "Transcribing... (2/5 chunks)"), and the "Process All" button is disabled
