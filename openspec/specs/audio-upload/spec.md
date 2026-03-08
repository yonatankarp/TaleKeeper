# Audio Upload

## Purpose

Allow the DM to upload pre-recorded audio files to a session, triggering automatic transcription and diarization processing with progress feedback.

## Requirements

### Requirement: Audio file upload
The system SHALL allow the DM to upload one or more audio files to a session. Each uploaded file SHALL be stored individually and tracked in `session_audio_files`. The system MUST accept common audio formats including m4a, mp3, wav, webm, ogg, and flac.

#### Scenario: Upload an audio file
- **WHEN** the DM selects an audio file via the file picker on the Recording tab
- **THEN** the file is uploaded to the backend, stored on disk, and added to the session's audio parts list

#### Scenario: Upload replaces existing audio (single-file fast path)
- **WHEN** the DM uploads a single audio file and immediately triggers processing
- **THEN** the file is set as the session's audio_path, existing transcript segments and speakers are cleared, and transcription begins

#### Scenario: Unsupported file type rejected
- **WHEN** the DM selects a non-audio file (e.g., a PDF or image)
- **THEN** the system rejects the upload with an error message indicating only audio files are accepted

### Requirement: Automatic processing after upload
The system SHALL automatically trigger transcription and speaker diarization after a successful audio upload. Processing progress SHALL be streamed to the frontend via Server-Sent Events.

#### Scenario: Full pipeline runs after upload
- **WHEN** an audio file upload completes successfully
- **THEN** the system runs chunked transcription followed by speaker diarization, streaming progress events to the frontend, and marks the session as completed when done

#### Scenario: Transcription progress displayed
- **WHEN** the uploaded audio is being transcribed
- **THEN** the frontend displays a progress indicator showing the current chunk being processed (e.g., "Transcribing chunk 3 of 50")

#### Scenario: Processing error
- **WHEN** transcription or diarization fails during processing
- **THEN** the system displays an error message, the session retains its uploaded audio file, and the DM can retry processing or use the retranscribe feature

### Requirement: Upload progress feedback
The system SHALL display upload progress while the audio file is being transferred to the backend. The upload button SHALL be disabled during upload and processing.

#### Scenario: Upload in progress
- **WHEN** the DM has selected a file and upload is in progress
- **THEN** the UI shows "Uploading..." and the upload and recording buttons are disabled

#### Scenario: Processing in progress
- **WHEN** the upload has completed and transcription is running
- **THEN** the UI shows transcription chunk progress and all recording/upload controls are disabled
