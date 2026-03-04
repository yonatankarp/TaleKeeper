# Speaker Diarization

## Purpose

Provide automatic speaker detection and identification using pyannote.audio's speaker diarization pipeline running on Apple GPU via MPS, aligning speakers with transcript segments, and enabling manual speaker name assignment and correction.

## Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically detect and distinguish different speakers in the audio using pyannote.audio's speaker diarization pipeline running on the Apple GPU via MPS. When voice signatures exist for the session's campaign, the system SHALL use signature-based nearest-neighbor matching as the primary identification method. When no signatures exist, the system SHALL use pyannote's built-in clustering. During final diarization, the system SHALL pass the campaign's `num_speakers` setting to pyannote for fixed-count speaker detection. Each detected speaker MUST be assigned a provisional label (e.g., "Player 1", "Player 2") or matched to a known roster entry name.

#### Scenario: Speakers detected with voice signatures
- **WHEN** a recording is processed and the campaign has voice signatures
- **THEN** the system matches audio segments against stored signatures and labels transcript segments with the matched roster entry names

#### Scenario: Speakers detected without voice signatures (cold start)
- **WHEN** a recording is processed and the campaign has no voice signatures
- **THEN** the system uses pyannote's built-in clustering and labels transcript segments with provisional identifiers (e.g., "Player 1", "Player 2")

#### Scenario: Single speaker detected
- **WHEN** only one person has spoken during the recording
- **THEN** all transcript segments are assigned to "Player 1" or the matched roster entry name

#### Scenario: Final diarization uses campaign speaker count
- **WHEN** a recording is stopped in a campaign with `num_speakers` set to 5
- **THEN** the final diarization pass uses pyannote with `num_speakers=5` to detect exactly 5 speaker groups

#### Scenario: Speaker count fetched from campaign
- **WHEN** `run_final_diarization` is called for a session
- **THEN** the system looks up the session's campaign and retrieves its `num_speakers` value, passing it to the pyannote pipeline

#### Scenario: Single speaker campaign
- **WHEN** a campaign has `num_speakers` set to 1
- **THEN** all transcript segments are assigned to a single speaker

#### Scenario: Retranscribe with speaker count override
- **WHEN** the user retranscribes a session with `num_speakers` set to 3
- **THEN** the final diarization pass uses pyannote with `num_speakers=3`, regardless of the campaign's default

#### Scenario: Recording with speaker count override
- **WHEN** the user sets `num_speakers` to 4 before recording
- **THEN** the final diarization after recording stop uses 4 speakers, regardless of the campaign's default

### Requirement: HuggingFace token for pyannote access
The system SHALL require a HuggingFace access token to download and use pyannote.audio's gated models. The token SHALL be configurable via the Settings page (stored in the `settings` table as `hf_token`) with an `HF_TOKEN` environment variable as fallback. The system SHALL display a clear error with setup instructions if no token is configured when diarization is attempted.

#### Scenario: Token configured via settings
- **WHEN** the DM enters a HuggingFace token in the Settings page
- **THEN** the token is stored in the settings table and used for pyannote model access

#### Scenario: Token configured via environment variable
- **WHEN** no `hf_token` is stored in settings but the `HF_TOKEN` environment variable is set
- **THEN** the system uses the environment variable value for pyannote model access

#### Scenario: No token configured
- **WHEN** diarization is triggered and no HuggingFace token is configured (neither settings nor env var)
- **THEN** the system returns an error with a message explaining that a HuggingFace token is required, including a link to the pyannote license agreement page

#### Scenario: HuggingFace token field in settings UI
- **WHEN** the DM opens the Settings page
- **THEN** a "HuggingFace Token" field is displayed in the Providers section with a link to the pyannote license agreement

### Requirement: Speaker-transcript alignment
The system SHALL align speaker diarization results with transcript segments so that each transcript segment is associated with exactly one speaker. When a single transcript segment contains speech from multiple speakers, it MUST be split at the speaker boundary. When using signature-based matching, speaker labels SHALL use the roster entry's player/character name directly instead of generic labels.

#### Scenario: Segments aligned with speakers
- **WHEN** diarization and transcription have both completed for a session
- **THEN** every transcript segment has exactly one speaker label and the speaker changes align with actual voice changes in the audio

#### Scenario: Segments aligned with known speakers
- **WHEN** diarization using voice signatures has completed for a session
- **THEN** every transcript segment has a speaker label matching a roster entry name, and the speaker changes align with actual voice changes in the audio

#### Scenario: Segments aligned with unknown speakers
- **WHEN** diarization has completed and some segments could not be matched to any voice signature
- **THEN** those segments are labeled "Unknown Speaker" and the user can manually reassign them

### Requirement: Manual speaker name assignment
The system SHALL allow the DM to assign player names and character names to all detected speakers in a single batch operation. The speaker panel MUST show all speakers simultaneously with input fields for player name and character name, roster quick-select buttons, a single "Save All" button that updates all speakers at once, and a "Merge into..." action per speaker for combining duplicate speakers. The assignment MUST update all transcript segments for each speaker in the session. The speaker list MAY shrink after user-initiated merges, reflecting that two detected speakers were the same person.

#### Scenario: Batch assign all speakers
- **WHEN** the DM clicks "Edit All" on the speaker panel with 4 detected speakers
- **THEN** a form appears showing all 4 speakers with their diarization labels, input fields for player name and character name, roster suggestion buttons, and a "Merge into..." action for each

#### Scenario: Save all speaker assignments at once
- **WHEN** the DM has filled in names for all speakers and clicks "Save All"
- **THEN** all speaker assignments are saved and all transcript segments are updated to reflect the new names

#### Scenario: Roster quick-select in batch mode
- **WHEN** the DM clicks a roster suggestion button next to a speaker in batch edit mode
- **THEN** that speaker's player name and character name fields are populated with the roster entry's values

#### Scenario: Cancel batch edit
- **WHEN** the DM clicks "Cancel" during batch editing
- **THEN** all edits are discarded and the speaker panel returns to its read-only view

#### Scenario: Speaker count reduced after merge
- **WHEN** the DM merges "Player 3" into "Player 1" in a session that originally had 4 detected speakers
- **THEN** the speaker panel shows 3 speakers and all transcript segments formerly attributed to "Player 3" now appear under "Player 1"

### Requirement: Speaker reassignment correction
The system SHALL allow the DM to reassign individual transcript segments to a different speaker. This corrects diarization errors without changing the global speaker mapping.

#### Scenario: Reassign a mislabeled segment
- **WHEN** a transcript segment is attributed to "Thorin" but the DM knows it was spoken by "Elara"
- **THEN** the DM can select that segment and reassign it to "Elara", updating only that segment's speaker association

#### Scenario: Bulk reassign segments
- **WHEN** the DM selects multiple consecutive transcript segments
- **THEN** the DM can reassign all selected segments to a different speaker in a single action

### Requirement: Speaker list from campaign roster
The system SHALL pre-populate the speaker name assignment UI with player and character names from the campaign's roster, if the session belongs to a campaign with a configured roster.

#### Scenario: Roster names available for assignment
- **WHEN** the DM opens speaker assignment for a session in a campaign with 5 players configured
- **THEN** the assignment dropdown shows all 5 player/character name pairs from the roster, plus an option to add a new speaker (e.g., for NPCs or guests)
