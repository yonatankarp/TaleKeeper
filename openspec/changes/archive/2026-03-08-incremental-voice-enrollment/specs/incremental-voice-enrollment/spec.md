## ADDED Requirements

### Requirement: Automatic voice enrollment on speaker-to-roster assignment
The system SHALL automatically extract a voice embedding and create or update a voice signature when a speaker is assigned to a roster entry via the speaker update endpoint. The enrollment SHALL run as a non-blocking background task so the speaker update response returns immediately.

#### Scenario: Speaker assigned to roster entry triggers enrollment
- **WHEN** a user updates a speaker's player_name and character_name to values matching an active roster entry in the session's campaign
- **THEN** the system schedules a background task that extracts voice embeddings from the speaker's transcript segments and creates a voice signature linked to that roster entry

#### Scenario: Speaker update with no roster match does not trigger enrollment
- **WHEN** a user updates a speaker's player_name and character_name to values that do not match any active roster entry
- **THEN** no voice enrollment is triggered and no voice signature is created or modified

#### Scenario: Speaker update with partial name does not trigger enrollment
- **WHEN** a user updates only the player_name (without character_name) or only the character_name (without player_name)
- **THEN** no voice enrollment is triggered

#### Scenario: Session without audio does not trigger enrollment
- **WHEN** a speaker is assigned to a roster entry but the session has no audio file
- **THEN** no voice enrollment is triggered and the speaker update succeeds normally

### Requirement: Audio sampling cap for enrollment
The system SHALL sample at most 120 seconds of audio per enrollment to keep processing time bounded. The system SHALL select transcript segments in order of decreasing duration (longest first) to maximize embedding quality.

#### Scenario: Speaker with less than 120 seconds of audio
- **WHEN** a speaker has transcript segments totalling 90 seconds of audio
- **THEN** all segments are used for embedding extraction

#### Scenario: Speaker with more than 120 seconds of audio
- **WHEN** a speaker has transcript segments totalling 300 seconds of audio
- **THEN** only the longest segments are used, up to a total of 120 seconds, and remaining segments are skipped

#### Scenario: Segment truncation at the cap boundary
- **WHEN** the accumulated duration is 115 seconds and the next segment is 20 seconds long
- **THEN** the system includes only the first 5 seconds of that segment (up to the 120-second cap), provided the remaining portion is at least 0.5 seconds

### Requirement: Weighted merge with existing voice signatures
The system SHALL weighted-merge new enrollment embeddings with any existing voice signature for the same roster entry. The merge SHALL use the formula: `combined = (old_embedding * old_count + new_embedding * new_count) / total_count`, followed by L2-normalization. The stored `num_samples` SHALL be updated to reflect the total count.

#### Scenario: First enrollment for a roster entry (no existing signature)
- **WHEN** a voice enrollment is triggered for a roster entry that has no existing voice signature
- **THEN** the system creates a new voice signature with the extracted embedding and sample count

#### Scenario: Subsequent enrollment merges with existing signature
- **WHEN** a voice enrollment is triggered for a roster entry that already has a voice signature with 10 samples
- **THEN** the system weighted-merges the new embedding with the existing one, L2-normalizes the result, and updates `num_samples` to `10 + new_count`

#### Scenario: Existing signature dominates when it has more samples
- **WHEN** an existing signature has 50 samples and a new enrollment adds 2 samples
- **THEN** the merged signature is heavily weighted toward the existing embedding direction

### Requirement: Enrollment failure handling
The system SHALL handle enrollment failures gracefully without affecting the speaker update operation. If enrollment fails (missing audio, embedding extraction error, database error), the system SHALL log a warning and continue — no user-facing error SHALL be raised.

#### Scenario: Audio file missing during enrollment
- **WHEN** enrollment is triggered but the session's audio file no longer exists on disk
- **THEN** enrollment fails silently with a log warning, and the speaker update that triggered it has already succeeded

#### Scenario: Embedding extraction returns no valid embeddings
- **WHEN** all of the speaker's segments are silence or too short for embedding extraction
- **THEN** enrollment completes without creating or modifying any voice signature
