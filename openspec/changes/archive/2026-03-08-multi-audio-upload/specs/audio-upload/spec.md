## MODIFIED Requirements

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
