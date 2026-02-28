## ADDED Requirements

### Requirement: Audio file upload
The system SHALL allow the DM to upload an audio file from their device to a session. The system MUST accept common audio formats including m4a, mp3, wav, webm, ogg, and flac. The uploaded file SHALL be stored in its original format without conversion.

#### Scenario: Upload an audio file
- **WHEN** the DM selects an audio file via the file picker on the Recording tab
- **THEN** the file is uploaded to the backend and saved to `data/audio/<campaign-id>/<session-id>.<original-extension>`

#### Scenario: Upload replaces existing audio
- **WHEN** the DM uploads an audio file to a session that already has audio
- **THEN** the existing audio file is deleted, existing transcript segments and speakers are cleared, and the new file is saved

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
