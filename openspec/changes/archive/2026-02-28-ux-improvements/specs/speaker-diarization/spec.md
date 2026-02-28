## MODIFIED Requirements

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
