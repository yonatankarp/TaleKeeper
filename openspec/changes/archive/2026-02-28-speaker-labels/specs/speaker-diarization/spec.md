## MODIFIED Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically run speaker diarization after recording stops and after retranscription completes. Detected speakers MUST be stored with friendly labels ("Player 1", "Player 2", etc.) derived from `enumerate(unique_labels, start=1)` rather than raw pyannote identifiers (e.g., "SPEAKER_00").

#### Scenario: Diarization runs after recording stops
- **WHEN** a recording session is stopped and audio chunks have been merged into the final WebM file
- **THEN** the system converts the WebM to WAV, runs `run_final_diarization()`, and cleans up the temporary WAV file

#### Scenario: Diarization runs after retranscription
- **WHEN** the DM triggers retranscription for a session
- **THEN** existing speakers for the session are deleted (`DELETE FROM speakers WHERE session_id = ?`), new transcript segments are created, and `run_final_diarization()` runs before the session is marked as completed

#### Scenario: Friendly speaker labels stored
- **WHEN** diarization detects 3 unique speakers in a session
- **THEN** the speakers table contains entries with `diarization_label` values "Player 1", "Player 2", "Player 3" (not "SPEAKER_00", "SPEAKER_01", "SPEAKER_02")

### Requirement: Speaker label display fallback chain
The frontend SHALL display speaker labels using a cascading fallback: character name + player name (e.g., "Thorin (Alice)") > character name only > player name only > diarization label > empty string. This fallback chain MUST be consistent between `TranscriptView` and `SpeakerPanel`.

#### Scenario: Full name display
- **WHEN** a speaker has both character_name "Thorin" and player_name "Alice"
- **THEN** the transcript segment and speaker panel display "Thorin (Alice)"

#### Scenario: Character name only
- **WHEN** a speaker has character_name "Thorin" but no player_name
- **THEN** the display shows "Thorin"

#### Scenario: Player name only
- **WHEN** a speaker has player_name "Alice" but no character_name
- **THEN** the display shows "Alice"

#### Scenario: Diarization label fallback
- **WHEN** a speaker has no character_name and no player_name but has diarization_label "Player 2"
- **THEN** the display shows "Player 2"

#### Scenario: No speaker information
- **WHEN** a transcript segment has no associated speaker
- **THEN** no speaker label is displayed

### Requirement: Transcript reload after retranscription
The frontend SHALL reload transcript segments from the API after retranscription completes so that speaker assignments from the post-transcription diarization pass are reflected in the UI.

#### Scenario: Segments populated with speakers after retranscribe
- **WHEN** retranscription finishes (including diarization) and the SSE stream ends
- **THEN** `TranscriptView` calls `load()` to fetch speaker-populated segments from the database, replacing the streamed segments that had no speaker data
