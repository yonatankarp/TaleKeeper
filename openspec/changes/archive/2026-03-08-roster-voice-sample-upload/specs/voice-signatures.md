# Delta Spec: voice-signatures (MODIFIED)

## ADDED: Requirement: Voice signature enrollment from uploaded audio sample

The system SHALL accept an audio file upload for any roster entry and use it to create or replace the roster entry's voice signature. The system SHALL truncate the audio to a maximum of 2 minutes before processing. The system SHALL run VAD and speaker embedding extraction on the uploaded audio and store the resulting embedding in the `voice_signatures` table with `source_session_id` set to NULL.

### Scenario: Successful voice sample upload

- **GIVEN** a roster entry with no existing voice signature
- **WHEN** the user uploads an audio file via the upload-voice-sample endpoint for that roster entry
- **THEN** the system converts the audio to 16kHz mono WAV, extracts a WeSpeaker embedding from the speech segments, and stores a voice signature linked to that roster entry with `source_session_id` NULL

### Scenario: Replace existing voice signature via upload

- **GIVEN** a roster entry with an existing voice signature
- **WHEN** the user uploads a new audio sample for that roster entry
- **THEN** the existing voice signature is deleted and replaced with the new one extracted from the uploaded sample

### Scenario: Audio longer than 2 minutes is truncated

- **GIVEN** a user uploads a 5-minute audio file
- **WHEN** the system processes the upload
- **THEN** only the first 2 minutes of audio are used for embedding extraction; the rest is discarded

### Scenario: No speech detected in uploaded audio

- **GIVEN** a user uploads an audio file with no detectable speech (e.g., silence or pure noise)
- **WHEN** the system attempts to extract an embedding
- **THEN** the endpoint returns an error indicating no speech was found and no voice signature is created

### Scenario: Unsupported or corrupt audio file

- **GIVEN** a user uploads a non-audio file or a corrupt audio file
- **WHEN** the system attempts to convert it
- **THEN** the endpoint returns an error and no voice signature is created

## ADDED: Requirement: Voice signature status on the Party screen

The system SHALL display, for each roster entry on the Party/Roster screen, whether a voice signature exists. The system SHALL show a visual indicator (badge or label) when a voice signature is present, including the number of embedding samples used to build it.

### Scenario: Signature present indicator

- **WHEN** the Party screen is displayed and a roster entry has a voice signature
- **THEN** that entry shows a "Voice signature" badge indicating the signature exists

### Scenario: No signature indicator

- **WHEN** the Party screen is displayed and a roster entry has no voice signature
- **THEN** no voice signature badge is shown for that entry, and only the upload button is available

### Scenario: Upload button triggers file picker

- **WHEN** the user clicks "Upload Voice Sample" for a roster entry
- **THEN** the system opens a file picker restricted to audio file types
- **AND** upon file selection the system uploads and processes the sample, showing a loading state until complete

### Scenario: Upload replaces existing signature

- **WHEN** the user uploads a new voice sample for a roster entry that already has a signature
- **THEN** after successful upload, the status indicator updates to reflect the new signature
