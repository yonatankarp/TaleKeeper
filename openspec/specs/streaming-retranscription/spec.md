# Streaming Retranscription

## Purpose

Provide a streaming retranscription capability that processes stored audio files via an SSE endpoint, delivering transcript segments progressively to the frontend as they are produced, with incremental persistence and bounded memory usage.

## Requirements

### Requirement: SSE streaming retranscription endpoint

The `POST /api/sessions/{session_id}/retranscribe` endpoint SHALL return a `StreamingResponse` with content type `text/event-stream`. Transcript segments SHALL be emitted as SSE events as they are produced by Whisper, rather than blocking until the entire file is processed.

#### Scenario: Segments are streamed as SSE events
- **WHEN** a retranscription request is made for a session with stored audio
- **THEN** the response is an SSE stream
- **AND** each transcript segment is emitted as an `event: segment` with JSON data containing `text`, `start_time`, and `end_time`

#### Scenario: Progress events are emitted between chunks
- **WHEN** processing moves from one audio chunk to the next during retranscription
- **THEN** an `event: progress` is emitted with JSON data containing `chunk` (current, 1-based) and `total_chunks`

#### Scenario: Done event signals completion
- **WHEN** all chunks have been transcribed
- **THEN** an `event: done` is emitted with JSON data containing `segments_count`
- **AND** the session status is updated to `completed`

#### Scenario: Session status is set to transcribing during processing
- **WHEN** retranscription begins
- **THEN** the session status is updated to `transcribing`
- **AND** existing transcript segments for the session are deleted before new ones are inserted

#### Scenario: Error during retranscription
- **WHEN** an error occurs during chunked retranscription
- **THEN** an `event: error` is emitted with JSON data containing `message`
- **AND** the session status is updated to `completed` (not left in `transcribing` state)

### Requirement: Chunked processing within SSE endpoint

The retranscription endpoint SHALL split the audio file into overlapping chunks (per the chunked-audio-processing spec), transcribe each chunk sequentially using `transcribe_stream()`, apply overlap deduplication, and emit segments as they are produced. Only one WAV chunk SHALL be in memory at a time.

#### Scenario: Large file is processed in chunks
- **WHEN** a 2-hour audio file is retranscribed
- **THEN** the file is split into 5-minute overlapping chunks
- **AND** each chunk is transcribed sequentially
- **AND** segments are streamed to the client as each chunk completes
- **AND** memory usage remains bounded regardless of file length

#### Scenario: Small file is processed as single chunk
- **WHEN** an audio file shorter than 5 minutes is retranscribed
- **THEN** it is processed as a single chunk without splitting
- **AND** segments are still streamed via SSE

### Requirement: Segment persistence during streaming

Each transcript segment SHALL be persisted to the `transcript_segments` database table as it is emitted via SSE, not batched until the end. This ensures partial results are preserved if the connection drops.

#### Scenario: Segments are persisted incrementally
- **WHEN** a segment SSE event is emitted
- **THEN** the segment is already inserted into the `transcript_segments` table

#### Scenario: Connection drops mid-retranscription
- **WHEN** the client disconnects during retranscription
- **THEN** all segments emitted before disconnection are persisted in the database

### Requirement: Frontend SSE consumption

The frontend SHALL consume the retranscription SSE stream using the `fetch` API with `ReadableStream` (not `EventSource`, which only supports GET). The UI SHALL display transcript segments progressively as they arrive and show chunk progress.

#### Scenario: Segments appear progressively in the UI
- **WHEN** retranscription is in progress
- **THEN** each segment appears in the transcript view as it arrives via SSE
- **AND** a progress indicator shows the current chunk and total chunks

#### Scenario: Retranscription completes
- **WHEN** the `done` event is received
- **THEN** the progress indicator is removed
- **AND** the transcript view shows the complete transcript

#### Scenario: Error handling
- **WHEN** an `error` event is received or the connection fails
- **THEN** the UI displays an error message
- **AND** any segments already received remain visible

### Requirement: Temporary WAV cleanup

All temporary WAV files created during retranscription (one per chunk) SHALL be deleted after the chunk is transcribed, in a `finally` block to ensure cleanup even on error.

#### Scenario: WAV files are cleaned up after each chunk
- **WHEN** a chunk's transcription completes (success or error)
- **THEN** the temporary WAV file for that chunk is deleted

#### Scenario: No temporary files remain after retranscription
- **WHEN** retranscription finishes (success, error, or client disconnect)
- **THEN** no temporary WAV files from this retranscription remain on disk
