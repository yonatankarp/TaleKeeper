## MODIFIED Requirements

### Requirement: Persistent audio storage
The system SHALL store audio files on the local filesystem, organized by campaign and session. Audio files MUST persist across application restarts. The system SHALL support storing audio in any format supported by ffmpeg, not limited to WebM.

#### Scenario: Audio file saved after recording
- **WHEN** a recording is stopped
- **THEN** the complete audio file is saved to `data/audio/<campaign-id>/<session-id>.webm` and the file path is recorded in the database

#### Scenario: Uploaded audio file saved
- **WHEN** an audio file is uploaded to a session
- **THEN** the file is saved to `data/audio/<campaign-id>/<session-id>.<original-extension>` and the file path is recorded in the database

#### Scenario: Audio survives restart
- **WHEN** the application is restarted after a session with a recording or uploaded audio
- **THEN** the audio file is still accessible and playable from the session view

### Requirement: Audio playback
The system SHALL allow the DM to play back audio for any completed session, whether the audio was recorded live or uploaded. Playback MUST support seeking to a specific timestamp. The audio endpoint SHALL serve the file with the correct MIME type derived from the file extension.

#### Scenario: Play session audio
- **WHEN** the DM opens a completed session and clicks play
- **THEN** the audio plays back in the browser with standard controls (play, pause, seek, volume)

#### Scenario: Seek to transcript timestamp
- **WHEN** the DM clicks on a transcript segment
- **THEN** audio playback seeks to the start time of that segment

#### Scenario: Correct MIME type for uploaded audio
- **WHEN** the DM plays back an uploaded .m4a file
- **THEN** the audio endpoint serves the file with `audio/mp4` content type
