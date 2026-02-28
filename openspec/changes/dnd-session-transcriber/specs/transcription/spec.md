## ADDED Requirements

### Requirement: On-device speech-to-text
The system SHALL transcribe audio using faster-whisper running locally on the DM's machine. Transcription MUST NOT require any network connectivity or cloud services.

#### Scenario: Transcribe session audio
- **WHEN** audio is being recorded or a completed recording is submitted for transcription
- **THEN** faster-whisper processes the audio on-device and produces text output with word-level timestamps

#### Scenario: No network required
- **WHEN** the machine has no internet connectivity
- **THEN** transcription functions identically to when the machine is online

### Requirement: Real-time transcription during recording
The system SHALL stream transcription results to the frontend in near-real-time while a recording is in progress. Transcript segments MUST appear within 5 seconds of the speech being captured.

#### Scenario: Live transcript updates
- **WHEN** the DM is actively recording a session
- **THEN** new transcript segments appear in the transcript view within 5 seconds of the words being spoken, streamed via WebSocket

#### Scenario: Transcript accumulates during recording
- **WHEN** a recording has been running for 30 minutes
- **THEN** the full transcript from the start of the session is visible and scrollable, with new segments appending at the bottom

### Requirement: Timestamped transcript segments
The system SHALL produce transcript segments with start and end timestamps aligned to the session audio timeline. Each segment MUST contain the transcribed text and its time range.

#### Scenario: Segment timestamps match audio
- **WHEN** the DM clicks on a transcript segment showing timestamp "00:12:30 - 00:12:45"
- **THEN** playing the audio from 00:12:30 produces speech matching the segment's text

### Requirement: Transcript persistence
The system SHALL store all transcript segments in the database, associated with their session. Transcripts MUST persist across application restarts.

#### Scenario: Transcript available after restart
- **WHEN** the application is restarted after a session has been transcribed
- **THEN** the full transcript is available when the DM opens that session

### Requirement: Whisper model selection
The system SHALL allow the DM to select which Whisper model size to use for transcription (e.g., tiny, base, small, medium, large-v3). The system MUST default to a model appropriate for the machine's capabilities.

#### Scenario: Change model size
- **WHEN** the DM changes the Whisper model size in settings
- **THEN** subsequent transcriptions use the newly selected model

#### Scenario: Default model selection
- **WHEN** the DM has not configured a model preference
- **THEN** the system defaults to the `medium` model as a balance of speed and accuracy

### Requirement: Re-transcription of stored audio
The system SHALL allow the DM to re-transcribe a previously recorded session using a different model or settings. Re-transcription MUST replace the existing transcript segments.

#### Scenario: Re-transcribe with larger model
- **WHEN** the DM selects "Re-transcribe" on a completed session and chooses the `large-v3` model
- **THEN** the system re-processes the stored audio file with the selected model, replaces the existing transcript segments, and preserves any speaker assignments that can be re-aligned

### Requirement: Transcription language
The system SHALL transcribe audio in English. The language MUST be explicitly set to English rather than relying on auto-detection.

#### Scenario: English language forced
- **WHEN** transcription is initiated
- **THEN** the Whisper model is configured with language set to English for optimal accuracy
