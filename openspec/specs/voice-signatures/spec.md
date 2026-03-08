# Voice Signatures

## Purpose

Enable per-speaker voice profile storage and matching at the campaign level, allowing the system to identify known speakers by comparing audio against stored voice embeddings instead of relying on unsupervised clustering.

## Requirements

### Requirement: Voice signature extraction from labeled sessions
The system SHALL extract voice signatures from sessions where speakers have been manually assigned to campaign roster entries. For each roster-linked speaker, the system SHALL compute an averaged, L2-normalized embedding from all transcript segments assigned to that speaker. The extraction SHALL reuse the existing ECAPA-TDNN encoder. Additionally, the system SHALL support incremental enrollment: when a speaker is assigned to a roster entry via the speaker update endpoint, the system SHALL automatically extract embeddings from that speaker's segments and create or weighted-merge the voice signature, without requiring an explicit "Generate Voice Signatures" action.

#### Scenario: Extract signatures from a fully labeled session
- **WHEN** a session has audio, transcript segments, and at least one speaker assigned to a roster entry, and the user triggers "Generate Voice Signatures"
- **THEN** the system extracts embeddings from each labeled speaker's segments using pyannote's embedding model, averages them into one 192-dim embedding per speaker, normalizes it, and stores it as a voice signature linked to the roster entry

#### Scenario: Partial labeling
- **WHEN** a session has 4 detected speakers but only 2 are assigned to roster entries
- **THEN** the system generates voice signatures only for the 2 assigned speakers and ignores the unassigned ones

#### Scenario: Regenerate existing signature
- **WHEN** a roster entry already has a voice signature and the user generates signatures from a new session via the explicit "Generate Voice Signatures" action
- **THEN** the existing signature for that roster entry is replaced with the new one extracted from the current session

#### Scenario: Incremental enrollment merges instead of replacing
- **WHEN** a roster entry already has a voice signature and incremental enrollment is triggered by a speaker assignment
- **THEN** the new embedding is weighted-merged with the existing signature rather than replacing it

### Requirement: Campaign-scoped voice signature storage
The system SHALL store voice signatures at the campaign level, linked to roster entries. Each roster entry SHALL have at most one voice signature. Signatures SHALL persist across sessions within the same campaign.

#### Scenario: Signature persists across sessions
- **WHEN** voice signatures are generated from Session 1
- **THEN** those signatures are available during diarization of Session 2 in the same campaign

#### Scenario: Deleting a roster entry removes its signature
- **WHEN** a roster entry with a voice signature is deleted
- **THEN** the associated voice signature is also deleted (CASCADE)

### Requirement: Signature-based speaker matching during diarization
The system SHALL use stored voice signatures as the primary speaker identification method when signatures exist for the session's campaign. For each audio segment, the system SHALL compute cosine similarity against all campaign signatures and assign the segment to the closest matching speaker above the campaign's configured similarity threshold.

#### Scenario: Diarization with signatures available
- **WHEN** a session is diarized and the campaign has voice signatures for 4 roster entries
- **THEN** each audio segment is compared against all 4 signatures and assigned to the best match above the campaign's similarity threshold

#### Scenario: Audio window below similarity threshold
- **WHEN** an audio segment's highest cosine similarity to any stored signature is below the campaign's configured similarity threshold
- **THEN** that segment is labeled as "Unknown Speaker"

#### Scenario: Fallback to clustering when no signatures exist
- **WHEN** a session is diarized and the campaign has no voice signatures
- **THEN** the system falls back to pyannote's built-in clustering

### Requirement: Voice signature management API
The system SHALL provide API endpoints to generate voice signatures from a session and to list existing signatures for a campaign.

#### Scenario: Generate signatures endpoint
- **WHEN** a POST request is made to the generate-signatures endpoint for a session
- **THEN** the system extracts signatures for all roster-linked speakers and returns the number of signatures generated and the number of audio samples per speaker

#### Scenario: List campaign signatures endpoint
- **WHEN** a GET request is made to the campaign signatures endpoint
- **THEN** the system returns all voice signatures for the campaign, including roster entry details and sample counts (but not the raw embedding data)

#### Scenario: Delete a specific signature
- **WHEN** a DELETE request is made for a specific voice signature
- **THEN** that signature is removed and future diarization for the campaign no longer matches against it

### Requirement: Voice signature UI controls
The system SHALL display a "Generate Voice Signatures" button in the speaker panel when the session has audio, transcript segments, and at least one speaker assigned to a roster entry. The system SHALL show which roster entries have existing voice signatures.

#### Scenario: Button visibility
- **WHEN** a session has audio and at least one speaker is linked to a roster entry
- **THEN** a "Generate Voice Signatures" button is visible in the speaker panel

#### Scenario: Button hidden when no roster links
- **WHEN** no speakers in the session are assigned to roster entries
- **THEN** the "Generate Voice Signatures" button is not shown

#### Scenario: Signature status indicators
- **WHEN** the speaker panel is displayed for a session in a campaign with voice signatures
- **THEN** each speaker linked to a roster entry with a signature shows a visual indicator (e.g., icon or badge) confirming a voice signature exists

### Requirement: Automatic signature invalidation on engine upgrade
The system SHALL automatically delete all voice signature data from the database when the embedding model changes in a way that makes existing embeddings incompatible. The invalidation SHALL run as a database migration during application startup.

#### Scenario: Signatures cleared on upgrade
- **WHEN** the application starts after upgrading from speechbrain to pyannote embeddings
- **THEN** all rows in the `voice_signatures` table are deleted
- **AND** users must re-enroll their players by generating new voice signatures

#### Scenario: UI indicates re-enrollment needed
- **WHEN** a campaign previously had voice signatures that were invalidated
- **THEN** the voice signature status indicators show that no signatures exist, prompting re-enrollment

### Requirement: Configurable similarity threshold
The system SHALL allow the DM to configure the cosine similarity threshold for voice signature matching on a per-campaign basis. The threshold SHALL be stored as a column on the `campaigns` table with a default value. The threshold SHALL be used by the `diarize_with_signatures` function instead of a hardcoded constant.

#### Scenario: Default threshold applied
- **WHEN** a campaign has no custom similarity threshold configured
- **THEN** voice signature matching uses the default threshold value

#### Scenario: Custom threshold per campaign
- **WHEN** the DM sets the similarity threshold to 0.8 for a specific campaign
- **THEN** voice signature matching for that campaign uses 0.8, while other campaigns use their own configured threshold

#### Scenario: Threshold editable in campaign settings
- **WHEN** the DM opens campaign settings
- **THEN** a "Voice Signature Confidence" slider or input field is available to adjust the similarity threshold

### Requirement: Voice signature enrollment from uploaded audio sample

The system SHALL accept an audio file upload for any roster entry and use it to create or replace the roster entry's voice signature. The system SHALL truncate the audio to a maximum of 2 minutes before processing. The system SHALL run VAD and speaker embedding extraction on the uploaded audio and store the resulting embedding in the `voice_signatures` table with `source_session_id` set to NULL.

#### Scenario: Successful voice sample upload

- **GIVEN** a roster entry with no existing voice signature
- **WHEN** the user uploads an audio file via the upload-voice-sample endpoint for that roster entry
- **THEN** the system converts the audio to 16kHz mono WAV, extracts a WeSpeaker embedding from the speech segments, and stores a voice signature linked to that roster entry with `source_session_id` NULL

#### Scenario: Replace existing voice signature via upload

- **GIVEN** a roster entry with an existing voice signature
- **WHEN** the user uploads a new audio sample for that roster entry
- **THEN** the existing voice signature is deleted and replaced with the new one extracted from the uploaded sample

#### Scenario: Audio longer than 2 minutes is truncated

- **GIVEN** a user uploads a 5-minute audio file
- **WHEN** the system processes the upload
- **THEN** only the first 2 minutes of audio are used for embedding extraction; the rest is discarded

#### Scenario: No speech detected in uploaded audio

- **GIVEN** a user uploads an audio file with no detectable speech (e.g., silence or pure noise)
- **WHEN** the system attempts to extract an embedding
- **THEN** the endpoint returns an error indicating no speech was found and no voice signature is created

#### Scenario: Unsupported or corrupt audio file

- **GIVEN** a user uploads a non-audio file or a corrupt audio file
- **WHEN** the system attempts to convert it
- **THEN** the endpoint returns an error and no voice signature is created

### Requirement: Voice signature status on the Party screen

The system SHALL display, for each roster entry on the Party/Roster screen, whether a voice signature exists. The system SHALL show a visual indicator (badge or label) when a voice signature is present, including the number of embedding samples used to build it.

#### Scenario: Signature present indicator

- **WHEN** the Party screen is displayed and a roster entry has a voice signature
- **THEN** that entry shows a "Voice ID" badge indicating the signature exists

#### Scenario: No signature indicator

- **WHEN** the Party screen is displayed and a roster entry has no voice signature
- **THEN** no voice signature badge is shown for that entry, and only the upload button is available

#### Scenario: Upload button triggers file picker

- **WHEN** the user clicks "Upload Voice Sample" for a roster entry
- **THEN** the system opens a file picker restricted to audio file types
- **AND** upon file selection the system uploads and processes the sample, showing a loading state until complete

#### Scenario: Upload replaces existing signature

- **WHEN** the user uploads a new voice sample for a roster entry that already has a signature
- **THEN** after successful upload, the status indicator updates to reflect the new signature
