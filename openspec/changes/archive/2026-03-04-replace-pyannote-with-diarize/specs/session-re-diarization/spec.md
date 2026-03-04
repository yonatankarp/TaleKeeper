## MODIFIED Requirements

### Requirement: SSE event contract for re-diarization
The re-diarize endpoint SHALL emit SSE events using the same event types as existing endpoints: `event: phase` with `{"phase": "diarization"}` at the start, `event: progress` with per-stage detail messages during processing, `event: done` with `{"segments_count": N}` on success, and `event: error` with `{"message": "..."}` on failure. Progress events SHALL report VAD completion (number of speech segments found), embedding extraction progress (X/Y per segment), and clustering result (speakers and segments found).

#### Scenario: Phase event emitted at start
- **WHEN** re-diarization begins
- **THEN** an `event: phase` SSE event is emitted with `{"phase": "diarization"}`
- **AND** an `event: progress` SSE event is emitted with detail "Detecting speech activity..."

#### Scenario: VAD progress reported during re-diarization
- **WHEN** voice activity detection completes during re-diarization
- **THEN** an `event: progress` SSE event is emitted with detail reporting the number of speech segments found and total speech duration

#### Scenario: Embedding progress reported during re-diarization
- **WHEN** embedding extraction is in progress during re-diarization with 400 speech segments
- **THEN** `event: progress` SSE events are emitted at regular intervals with detail "Extracting speaker embeddings (X/400)..."

#### Scenario: Clustering progress reported during re-diarization
- **WHEN** spectral clustering completes during re-diarization
- **THEN** an `event: progress` SSE event is emitted with detail reporting the number of speakers and segments found

#### Scenario: Done event emitted on success
- **WHEN** re-diarization completes successfully and the session has 50 transcript segments
- **THEN** an `event: done` SSE event is emitted with `{"segments_count": 50}`

#### Scenario: Error event emitted on failure
- **WHEN** an exception occurs during re-diarization
- **THEN** an `event: error` SSE event is emitted with `{"message": "<error details>"}`
