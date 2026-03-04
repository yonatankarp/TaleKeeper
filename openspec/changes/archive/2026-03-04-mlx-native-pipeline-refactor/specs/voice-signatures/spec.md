# Voice Signatures

## MODIFIED Requirements

### Requirement: Voice signature extraction from labeled sessions
The system SHALL extract voice signatures from sessions where speakers have been manually assigned to campaign roster entries. For each roster-linked speaker, the system SHALL compute an averaged, L2-normalized 192-dimensional embedding from all transcript segments assigned to that speaker using pyannote's embedding model (`pyannote/embedding`).

#### Scenario: Extract signatures from a fully labeled session
- **WHEN** a session has audio, transcript segments, and at least one speaker assigned to a roster entry, and the user triggers "Generate Voice Signatures"
- **THEN** the system extracts embeddings from each labeled speaker's segments using pyannote's embedding model, averages them into one 192-dim embedding per speaker, normalizes it, and stores it as a voice signature linked to the roster entry

#### Scenario: Partial labeling
- **WHEN** a session has 4 detected speakers but only 2 are assigned to roster entries
- **THEN** the system generates voice signatures only for the 2 assigned speakers and ignores the unassigned ones

#### Scenario: Regenerate existing signature
- **WHEN** a roster entry already has a voice signature and the user generates signatures from a new session
- **THEN** the existing signature for that roster entry is replaced with the new one extracted from the current session

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

## ADDED Requirements

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
