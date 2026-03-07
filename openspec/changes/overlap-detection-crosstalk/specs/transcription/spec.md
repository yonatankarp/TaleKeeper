## ADDED Requirements

### Requirement: Overlap flag on transcript segments
The system SHALL store an `is_overlap` boolean column on the `transcript_segments` table (stored as `INTEGER`, default 0). Segments flagged by overlap detection MUST have `is_overlap = 1` and `speaker_id = NULL`. Segments not flagged MUST have `is_overlap = 0`. The column MUST be added via an additive migration and existing rows default to 0.

#### Scenario: Overlap segment persisted correctly
- **WHEN** a transcript segment is aligned to a `[crosstalk]` diarization segment
- **THEN** the segment is stored with `is_overlap = 1` and `speaker_id = NULL`

#### Scenario: Normal segment persisted correctly
- **WHEN** a transcript segment is attributed to a specific speaker
- **THEN** the segment is stored with `is_overlap = 0` and a valid `speaker_id`

#### Scenario: Existing sessions unaffected by migration
- **WHEN** the migration runs on a database containing previously transcribed sessions
- **THEN** all existing `transcript_segments` rows have `is_overlap = 0` and their `speaker_id` values are unchanged

#### Scenario: Transcript available after restart includes overlap flag
- **WHEN** the application is restarted after a session has been transcribed with overlap detection enabled
- **THEN** the full transcript is available and each segment retains its `is_overlap` value
