# Chunked Audio Processing

## Purpose

Provide disk-based chunked audio handling for recording and retranscription, ensuring bounded memory usage regardless of recording duration, incremental live transcription of new chunks only, and overlap-aware deduplication when splitting stored files for retranscription.

## Requirements

### Requirement: Disk-based chunk storage during recording

The system SHALL write each incoming WebSocket audio chunk to a numbered file on disk (`chunk_000.webm`, `chunk_001.webm`, ...) in a temporary directory at `data/audio/<campaign_id>/tmp_<session_id>/` instead of accumulating chunks in memory. The system SHALL NOT hold more than one chunk's worth of audio data in memory at any time during recording.

#### Scenario: Chunks are written to disk as they arrive
- **WHEN** the WebSocket receives a binary audio chunk during recording
- **THEN** the chunk is written to a sequentially numbered file in the temporary chunk directory

#### Scenario: Chunk directory is created on recording start
- **WHEN** a recording WebSocket connection is established for a session
- **THEN** a temporary directory is created at `data/audio/<campaign_id>/tmp_<session_id>/`

#### Scenario: Memory remains bounded during long recordings
- **WHEN** a recording runs for any duration (including 3-4+ hours)
- **THEN** the system's in-memory audio buffer SHALL NOT grow beyond the size of a single chunk batch (~10 seconds of audio)

### Requirement: Chunk merging on recording stop

The system SHALL concatenate all chunk files into a single `.webm` file at `data/audio/<campaign_id>/<session_id>.webm` when recording stops, then delete the temporary chunk directory. The final merged file SHALL be byte-identical to what the current implementation produces.

#### Scenario: Successful merge on normal stop
- **WHEN** the user stops recording (sends "stop" message or WebSocket disconnects)
- **THEN** all chunk files are concatenated in order into a single `.webm` file at the standard audio path
- **AND** the temporary chunk directory is deleted
- **AND** the session's `audio_path` and `status` are updated in the database

#### Scenario: No chunks recorded
- **WHEN** recording stops but no audio chunks were received
- **THEN** no audio file is created
- **AND** the session status is set to `draft`
- **AND** the temporary chunk directory is cleaned up

#### Scenario: Orphaned chunk directories are cleaned on startup
- **WHEN** the application starts
- **THEN** any `tmp_*` directories under `data/audio/` are deleted

### Requirement: Incremental-only live transcription

The system SHALL transcribe only the new chunks received since the last transcription cycle (every ~10 chunks), not the entire accumulated audio. Transcript segment timestamps SHALL be adjusted by a running time offset so they reflect the correct position in the full recording.

#### Scenario: Only new chunks are transcribed
- **WHEN** the transcription interval fires (every 10 chunks)
- **THEN** only the chunk files written since the last transcription are concatenated, converted to WAV, and transcribed
- **AND** the full accumulated buffer is NOT re-processed

#### Scenario: Timestamps are offset-adjusted
- **WHEN** a new chunk batch is transcribed
- **THEN** the resulting segment timestamps are adjusted by adding the cumulative duration of all previously transcribed chunks
- **AND** the cumulative offset is advanced by the duration of the current chunk batch

#### Scenario: Transcription results are streamed back and persisted
- **WHEN** incremental transcription produces segments
- **THEN** each segment is sent to the client via the WebSocket as a `{"type": "transcript"}` message
- **AND** each segment is persisted to the `transcript_segments` table

### Requirement: Audio file splitting for retranscription

The system SHALL provide a function to split a stored audio file into overlapping segments of 5 minutes with 30-second overlap on each side. Each segment SHALL be exported as a temporary WAV file (16kHz mono). Only one segment SHALL be held in memory at a time.

#### Scenario: File is split into overlapping chunks
- **WHEN** a stored audio file is submitted for chunked retranscription
- **THEN** the file is split into 5-minute segments with 30-second overlap
- **AND** each segment is exported as a temporary WAV file

#### Scenario: Short audio files are not split
- **WHEN** an audio file is shorter than or equal to 5 minutes
- **THEN** the file is processed as a single chunk without splitting

#### Scenario: Segment boundaries for a 12-minute file
- **WHEN** a 12-minute audio file is split
- **THEN** the chunks are: 0:00-5:00, 4:30-9:30, 9:00-12:00

### Requirement: Overlap deduplication for chunked transcription

The system SHALL deduplicate transcript segments from overlapping chunk regions using a midpoint-based primary zone strategy. Each chunk owns segments whose temporal midpoint falls within its non-overlapping interior.

#### Scenario: Interior segments are kept, edge segments are discarded
- **WHEN** two adjacent chunks produce segments in their 30-second overlap region
- **THEN** only the segment from the chunk whose primary zone contains the segment's midpoint is kept

#### Scenario: First chunk owns segments up to overlap midpoint
- **WHEN** chunk 0 spans 0:00-5:00 and chunk 1 spans 4:30-9:30
- **THEN** chunk 0 keeps segments with midpoint in 0:00-4:45
- **AND** chunk 1 keeps segments with midpoint in 4:45-9:15

#### Scenario: Last chunk keeps all remaining segments
- **WHEN** the final chunk is being processed
- **THEN** all segments with midpoint at or after the chunk's primary zone start are kept
