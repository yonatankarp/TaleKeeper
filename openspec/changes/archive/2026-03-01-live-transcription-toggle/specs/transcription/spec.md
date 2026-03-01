## MODIFIED Requirements

### Requirement: Real-time transcription during recording
The system SHALL stream transcription results to the frontend in near-real-time while a recording is in progress, ONLY when the session's campaign has `live_transcription` enabled. When `live_transcription` is disabled, no incremental transcript segments SHALL be produced during recording.

#### Scenario: Live transcript updates with live transcription enabled
- **WHEN** the DM is actively recording a session in a campaign with `live_transcription` enabled
- **THEN** new transcript segments appear in the transcript view within 5 seconds of the words being spoken, streamed via WebSocket

#### Scenario: No live transcript when live transcription disabled
- **WHEN** the DM is actively recording a session in a campaign with `live_transcription` disabled (the default)
- **THEN** no transcript segments appear during recording; the transcript view shows "Waiting for speech..." until recording stops and full processing begins

#### Scenario: Transcript accumulates during recording
- **WHEN** a recording has been running for 30 minutes in a campaign with `live_transcription` enabled
- **THEN** the full transcript from the start of the session is visible and scrollable, with new segments appending at the bottom

## ADDED Requirements

### Requirement: Preview banner during post-recording processing
The system SHALL display a processing banner in the transcript view when audio is being processed after recording stops. When live transcription segments are present, the banner MUST clearly indicate that segments are a preview and full-quality transcription is in progress. When no segments are present, the banner MUST indicate processing is underway.

#### Scenario: Preview banner with live transcription segments
- **WHEN** recording has stopped in a campaign with `live_transcription` enabled and the session status is `audio_ready` or `transcribing` and transcript segments exist
- **THEN** the transcript view shows a banner: "Segments below are a preview from live transcription. Full-quality transcription is in progress..."

#### Scenario: Processing banner without live transcription segments
- **WHEN** recording has stopped in a campaign with `live_transcription` disabled and the session status is `audio_ready` or `transcribing` and no transcript segments exist
- **THEN** the transcript view shows a banner: "Processing audio — transcribing and identifying speakers..."

#### Scenario: Banner disappears after processing completes
- **WHEN** the session status transitions to `completed`
- **THEN** the processing/preview banner is removed and the final transcript with speaker labels is displayed
