## ADDED Requirements

### Requirement: Re-diarization SSE endpoint
The system SHALL provide a `POST /api/sessions/{session_id}/re-diarize` endpoint that re-runs speaker diarization on a completed session without re-running transcription. The endpoint SHALL accept a JSON body with a required `num_speakers` field (integer, 1-10). The endpoint SHALL return a `StreamingResponse` with content type `text/event-stream`. The endpoint SHALL reject requests when the session status is not `completed` (HTTP 409). The endpoint SHALL reject requests when the session has no audio file (HTTP 400).

#### Scenario: Successful re-diarization
- **WHEN** a POST request is made to `/api/sessions/{session_id}/re-diarize` with `{"num_speakers": 4}` for a completed session with audio
- **THEN** the system re-runs diarization with 4 speakers and streams SSE events reporting progress and completion

#### Scenario: Session not completed
- **WHEN** a POST request is made to `/api/sessions/{session_id}/re-diarize` for a session with status `transcribing` or `diarizing`
- **THEN** the system returns HTTP 409 with detail "Session is currently being processed"

#### Scenario: Session has no audio
- **WHEN** a POST request is made to `/api/sessions/{session_id}/re-diarize` for a session with no audio file
- **THEN** the system returns HTTP 400 with detail "No audio recorded for this session"

#### Scenario: Invalid num_speakers
- **WHEN** a POST request is made with `num_speakers` outside the range 1-10 or missing
- **THEN** the system returns HTTP 422 (validation error)

### Requirement: Old speaker data cleanup before re-diarization
The system SHALL clean up existing speaker data for the session before running re-diarization. The cleanup sequence SHALL be: (1) set `speaker_id = NULL` on all transcript segments for the session, (2) delete voice signatures where `source_session_id` matches the session, (3) delete all speaker rows for the session. Campaign-level voice signatures from other sessions SHALL NOT be deleted.

#### Scenario: Transcript segments preserved with speaker_id cleared
- **WHEN** re-diarization begins on a session with 50 transcript segments assigned to 3 speakers
- **THEN** all 50 transcript segments retain their text, start_time, and end_time unchanged
- **AND** all 50 transcript segments have `speaker_id` set to NULL before new diarization runs

#### Scenario: Session-sourced voice signatures deleted
- **WHEN** re-diarization begins on session 5, and session 5 previously generated voice signatures for 3 roster entries
- **THEN** the voice signatures with `source_session_id = 5` are deleted
- **AND** voice signatures generated from other sessions in the same campaign are preserved

#### Scenario: Old speaker rows deleted
- **WHEN** re-diarization begins on a session with 4 existing speakers
- **THEN** all 4 speaker rows for the session are deleted before new speakers are created by the diarization pass

### Requirement: Session status lifecycle during re-diarization
The system SHALL set the session status to `diarizing` when re-diarization begins and back to `completed` when it finishes (whether successful or failed). This status SHALL prevent concurrent operations on the same session.

#### Scenario: Status set to diarizing during processing
- **WHEN** re-diarization starts on a session
- **THEN** the session status is updated to `diarizing`

#### Scenario: Status restored to completed on success
- **WHEN** re-diarization completes successfully
- **THEN** the session status is updated to `completed`

#### Scenario: Status restored to completed on error
- **WHEN** an error occurs during re-diarization
- **THEN** an `event: error` SSE event is emitted with a message
- **AND** the session status is updated to `completed`

### Requirement: SSE event contract for re-diarization
The re-diarize endpoint SHALL emit SSE events using the same event types as existing endpoints: `event: phase` with `{"phase": "diarization"}` at the start, `event: done` with `{"segments_count": N}` on success, and `event: error` with `{"message": "..."}` on failure.

#### Scenario: Phase event emitted at start
- **WHEN** re-diarization begins
- **THEN** an `event: phase` SSE event is emitted with `{"phase": "diarization"}`

#### Scenario: Done event emitted on success
- **WHEN** re-diarization completes successfully and the session has 50 transcript segments
- **THEN** an `event: done` SSE event is emitted with `{"segments_count": 50}`

#### Scenario: Error event emitted on failure
- **WHEN** an exception occurs during re-diarization
- **THEN** an `event: error` SSE event is emitted with `{"message": "<error details>"}`

### Requirement: Voice signature matching during re-diarization
The re-diarize endpoint SHALL use campaign voice signatures (from other sessions) for speaker matching when available, following the same logic as initial diarization. When no campaign voice signatures exist, unsupervised clustering with the provided `num_speakers` SHALL be used.

#### Scenario: Re-diarize with campaign voice signatures
- **WHEN** re-diarization runs on a session whose campaign has voice signatures for 3 roster entries (generated from other sessions)
- **THEN** the system uses signature-based matching against those 3 voice signatures

#### Scenario: Re-diarize without voice signatures
- **WHEN** re-diarization runs on a session whose campaign has no voice signatures
- **THEN** the system uses unsupervised agglomerative clustering with the provided `num_speakers` count

### Requirement: Re-diarize button in transcript view
The frontend SHALL display a "Re-diarize" button in the retranscribe bar, next to the existing "Retranscribe" button. The button SHALL share the existing speaker count input. The button SHALL be disabled when a transcription or diarization operation is in progress. Clicking the button SHALL show a confirmation dialog warning that existing speaker assignments will be lost.

#### Scenario: Button visible for completed session with audio
- **WHEN** a session has audio, is not recording, and has status other than `transcribing` or `diarizing`
- **THEN** a "Re-diarize" button is visible in the retranscribe bar next to the "Retranscribe" button

#### Scenario: Button disabled during processing
- **WHEN** the session status is `transcribing` or `diarizing`
- **THEN** the "Re-diarize" button is disabled

#### Scenario: Confirmation dialog before re-diarization
- **WHEN** the user clicks the "Re-diarize" button
- **THEN** a confirmation dialog is shown warning that existing speaker assignments and session-generated voice signatures will be lost
- **AND** the user must confirm before the operation proceeds

#### Scenario: Frontend consumes SSE stream
- **WHEN** the user confirms re-diarization
- **THEN** the frontend sends a POST to `/api/sessions/{session_id}/re-diarize` with the selected speaker count
- **AND** consumes the SSE stream, showing progress
- **AND** refreshes the speaker panel and transcript view on completion

### Requirement: Temporary WAV cleanup
All temporary WAV files created during re-diarization SHALL be deleted after diarization completes, in a `finally` block to ensure cleanup even on error.

#### Scenario: WAV file cleaned up on success
- **WHEN** re-diarization completes successfully
- **THEN** the temporary WAV file is deleted

#### Scenario: WAV file cleaned up on error
- **WHEN** an error occurs during re-diarization
- **THEN** the temporary WAV file is still deleted
