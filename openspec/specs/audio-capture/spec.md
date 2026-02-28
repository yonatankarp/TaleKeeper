# Audio Capture

## Purpose

Provide browser-based audio recording capabilities for D&D sessions, including microphone access management, recording lifecycle control, audio encoding, persistent storage, and playback functionality.

## Requirements

### Requirement: Microphone access and permission
The system SHALL request microphone access from the browser when the DM starts a recording. The system MUST display a clear error message if microphone permission is denied or no microphone is available.

#### Scenario: First-time microphone access
- **WHEN** the DM clicks "Start Recording" and the browser has not yet granted microphone permission
- **THEN** the browser's native permission prompt is triggered and recording begins only after permission is granted

#### Scenario: Microphone permission denied
- **WHEN** the DM denies microphone permission or no microphone device is detected
- **THEN** the system displays an error message explaining that microphone access is required and how to enable it in browser settings

### Requirement: Audio recording lifecycle
The system SHALL support starting, pausing, resuming, and stopping an audio recording within a session. Only one recording SHALL be active at a time across the entire application.

#### Scenario: Start recording
- **WHEN** the DM starts a new recording within a session
- **THEN** the system begins capturing audio from the microphone, displays a recording indicator with elapsed time, and streams audio chunks to the backend via WebSocket

#### Scenario: Pause and resume recording
- **WHEN** the DM pauses an active recording
- **THEN** audio capture stops, the recording indicator shows "Paused", and the DM can resume recording to continue the same session's audio

#### Scenario: Stop recording
- **WHEN** the DM stops an active recording
- **THEN** audio capture stops, the final audio file is saved to persistent storage, and the session transitions to "completed" status

#### Scenario: Prevent concurrent recordings
- **WHEN** a recording is active and the DM attempts to start a new recording in a different session
- **THEN** the system prevents the new recording and prompts the DM to stop the current recording first

### Requirement: Audio encoding format
The system SHALL record audio using the WebM container with Opus codec via the browser's MediaRecorder API. Audio MUST be captured in mono at a sample rate of 44100 Hz.

#### Scenario: Audio format configuration
- **WHEN** the system initializes the MediaRecorder for a new recording
- **THEN** it requests mono audio at 44100 Hz with Opus codec, falling back to the browser's default codec if Opus is unavailable

### Requirement: Persistent audio storage
The system SHALL store recorded audio files on the local filesystem, organized by campaign and session. Audio files MUST persist across application restarts.

#### Scenario: Audio file saved after recording
- **WHEN** a recording is stopped
- **THEN** the complete audio file is saved to `data/audio/<campaign-id>/<session-id>.webm` and the file path is recorded in the database

#### Scenario: Audio survives restart
- **WHEN** the application is restarted after a session with a recording
- **THEN** the audio file is still accessible and playable from the session view

### Requirement: Audio playback
The system SHALL allow the DM to play back recorded audio for any completed session. Playback MUST support seeking to a specific timestamp.

#### Scenario: Play session audio
- **WHEN** the DM opens a completed session and clicks play
- **THEN** the audio plays back in the browser with standard controls (play, pause, seek, volume)

#### Scenario: Seek to transcript timestamp
- **WHEN** the DM clicks on a transcript segment
- **THEN** audio playback seeks to the start time of that segment
