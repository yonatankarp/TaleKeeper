# Speaker Diarization

## Purpose

Provide automatic speaker detection and identification using pyannote-audio, aligning speakers with transcript segments, supporting real-time provisional labels during recording, and enabling manual speaker name assignment and correction.

## Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically detect and distinguish different speakers in the audio using pyannote-audio. Each detected speaker MUST be assigned a provisional label (e.g., "Speaker 1", "Speaker 2").

#### Scenario: Speakers detected during recording
- **WHEN** a recording is in progress with multiple people speaking
- **THEN** the system detects distinct speakers and labels transcript segments with provisional speaker identifiers (e.g., "Speaker 1", "Speaker 2")

#### Scenario: Single speaker detected
- **WHEN** only one person has spoken during the recording
- **THEN** all transcript segments are assigned to "Speaker 1"

### Requirement: Speaker-transcript alignment
The system SHALL align speaker diarization results with transcript segments so that each transcript segment is associated with exactly one speaker. When a single transcript segment contains speech from multiple speakers, it MUST be split at the speaker boundary.

#### Scenario: Segments aligned with speakers
- **WHEN** diarization and transcription have both completed for a session
- **THEN** every transcript segment has exactly one speaker label and the speaker changes align with actual voice changes in the audio

### Requirement: Near-real-time diarization during recording
The system SHALL run diarization on buffered audio chunks during recording and send provisional speaker labels to the frontend. Speaker labels MAY change as more audio context becomes available.

#### Scenario: Provisional labels during recording
- **WHEN** the DM is recording and two different people have spoken
- **THEN** transcript segments in the live view show different provisional speaker labels, which may be refined as more audio is processed

#### Scenario: Labels stabilize after recording ends
- **WHEN** a recording is stopped
- **THEN** the system runs a final diarization pass on the complete audio to produce stable, consistent speaker labels across the entire session

### Requirement: Manual speaker name assignment
The system SHALL allow the DM to assign player names and character names to all detected speakers in a single batch operation. The speaker panel MUST show all speakers simultaneously with input fields for player name and character name, roster quick-select buttons, and a single "Save All" button that updates all speakers at once. The assignment MUST update all transcript segments for each speaker in the session.

#### Scenario: Batch assign all speakers
- **WHEN** the DM clicks "Edit All" on the speaker panel with 4 detected speakers
- **THEN** a form appears showing all 4 speakers with their diarization labels, input fields for player name and character name, and roster suggestion buttons for each

#### Scenario: Save all speaker assignments at once
- **WHEN** the DM has filled in names for all speakers and clicks "Save All"
- **THEN** all speaker assignments are saved and all transcript segments are updated to reflect the new names

#### Scenario: Roster quick-select in batch mode
- **WHEN** the DM clicks a roster suggestion button next to a speaker in batch edit mode
- **THEN** that speaker's player name and character name fields are populated with the roster entry's values

#### Scenario: Cancel batch edit
- **WHEN** the DM clicks "Cancel" during batch editing
- **THEN** all edits are discarded and the speaker panel returns to its read-only view

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
