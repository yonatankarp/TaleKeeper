# Voice Signatures

## Purpose

Enable per-speaker voice profile storage and matching at the campaign level, allowing the system to identify known speakers by comparing audio against stored voice embeddings instead of relying on unsupervised clustering.

## ADDED Requirements

### Requirement: Voice signature extraction from labeled sessions
The system SHALL extract voice signatures from sessions where speakers have been manually assigned to campaign roster entries. For each roster-linked speaker, the system SHALL compute an averaged, L2-normalized embedding from all transcript segments assigned to that speaker. The extraction SHALL reuse the existing ECAPA-TDNN encoder.

#### Scenario: Extract signatures from a fully labeled session
- **WHEN** a session has audio, transcript segments, and at least one speaker assigned to a roster entry, and the user triggers "Generate Voice Signatures"
- **THEN** the system extracts windowed embeddings from each labeled speaker's segments, averages them into one embedding per speaker, normalizes it, and stores it as a voice signature linked to the roster entry

#### Scenario: Partial labeling
- **WHEN** a session has 4 detected speakers but only 2 are assigned to roster entries
- **THEN** the system generates voice signatures only for the 2 assigned speakers and ignores the unassigned ones

#### Scenario: Regenerate existing signature
- **WHEN** a roster entry already has a voice signature and the user generates signatures from a new session
- **THEN** the existing signature for that roster entry is replaced with the new one extracted from the current session

### Requirement: Campaign-scoped voice signature storage
The system SHALL store voice signatures at the campaign level, linked to roster entries. Each roster entry SHALL have at most one voice signature. Signatures SHALL persist across sessions within the same campaign.

#### Scenario: Signature persists across sessions
- **WHEN** voice signatures are generated from Session 1
- **THEN** those signatures are available during diarization of Session 2 in the same campaign

#### Scenario: Deleting a roster entry removes its signature
- **WHEN** a roster entry with a voice signature is deleted
- **THEN** the associated voice signature is also deleted (CASCADE)

### Requirement: Signature-based speaker matching during diarization
The system SHALL use stored voice signatures as the primary speaker identification method when signatures exist for the session's campaign. For each audio window, the system SHALL compute cosine similarity against all campaign signatures and assign the window to the closest matching speaker above a minimum similarity threshold.

#### Scenario: Diarization with signatures available
- **WHEN** a session is diarized and the campaign has voice signatures for 4 roster entries
- **THEN** each audio window is compared against all 4 signatures and assigned to the best match above the similarity threshold

#### Scenario: Audio window below similarity threshold
- **WHEN** an audio window's highest cosine similarity to any stored signature is below the minimum threshold
- **THEN** that window is labeled as "Unknown Speaker"

#### Scenario: Fallback to clustering when no signatures exist
- **WHEN** a session is diarized and the campaign has no voice signatures
- **THEN** the system falls back to unsupervised agglomerative clustering

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
