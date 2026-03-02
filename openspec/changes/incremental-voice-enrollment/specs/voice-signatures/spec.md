## MODIFIED Requirements

### Requirement: Voice signature extraction from labeled sessions
The system SHALL extract voice signatures from sessions where speakers have been manually assigned to campaign roster entries. For each roster-linked speaker, the system SHALL compute an averaged, L2-normalized embedding from all transcript segments assigned to that speaker. The extraction SHALL reuse the existing ECAPA-TDNN encoder. Additionally, the system SHALL support incremental enrollment: when a speaker is assigned to a roster entry via the speaker update endpoint, the system SHALL automatically extract embeddings from that speaker's segments and create or weighted-merge the voice signature, without requiring an explicit "Generate Voice Signatures" action.

#### Scenario: Extract signatures from a fully labeled session
- **WHEN** a session has audio, transcript segments, and at least one speaker assigned to a roster entry, and the user triggers "Generate Voice Signatures"
- **THEN** the system extracts windowed embeddings from each labeled speaker's segments, averages them into one embedding per speaker, normalizes it, and stores it as a voice signature linked to the roster entry

#### Scenario: Partial labeling
- **WHEN** a session has 4 detected speakers but only 2 are assigned to roster entries
- **THEN** the system generates voice signatures only for the 2 assigned speakers and ignores the unassigned ones

#### Scenario: Regenerate existing signature
- **WHEN** a roster entry already has a voice signature and the user generates signatures from a new session via the explicit "Generate Voice Signatures" action
- **THEN** the existing signature for that roster entry is replaced with the new one extracted from the current session

#### Scenario: Incremental enrollment merges instead of replacing
- **WHEN** a roster entry already has a voice signature and incremental enrollment is triggered by a speaker assignment
- **THEN** the new embedding is weighted-merged with the existing signature rather than replacing it
