# Audio Capture

## MODIFIED Requirements

### Requirement: Audio recording lifecycle
The system SHALL support starting, pausing, resuming, and stopping an audio recording within a session. Only one recording SHALL be active at a time across the entire application. The WebSocket recording endpoint SHALL handle audio chunk capture only — no transcription or diarization processing SHALL occur during recording.

#### Scenario: Start recording
- **WHEN** the DM starts a new recording within a session
- **THEN** the system begins capturing audio from the microphone, displays a recording indicator with elapsed time, and streams audio chunks to the backend via WebSocket for disk storage only

#### Scenario: Pause and resume recording
- **WHEN** the DM pauses an active recording
- **THEN** audio capture stops, the recording indicator shows "Paused", and the DM can resume recording to continue the same session's audio

#### Scenario: Stop recording
- **WHEN** the DM stops an active recording
- **THEN** audio capture stops, the final audio file is saved to persistent storage, and the session transitions to `audio_ready` status ready for processing

#### Scenario: Prevent concurrent recordings
- **WHEN** a recording is active and the DM attempts to start a new recording in a different session
- **THEN** the system prevents the new recording and prompts the DM to stop the current recording first
