## MODIFIED Requirements

### Requirement: Campaign CRUD
The system SHALL allow the DM to create, view, edit, and delete campaigns. Each campaign MUST have a name, MAY have an optional description, MUST have a `num_speakers` field (integer, 1–10, default 5) indicating how many speakers to expect during diarization, and MUST have a `live_transcription` field (boolean, default false) controlling whether incremental transcription runs during recording.

#### Scenario: Create a campaign
- **WHEN** the DM creates a new campaign with the name "Curse of Strahd"
- **THEN** the campaign is created with `num_speakers` defaulting to 5 and `live_transcription` defaulting to false, appears in the campaign list, and is available for adding sessions

#### Scenario: Create campaign with custom speaker count
- **WHEN** the DM creates a campaign and sets `num_speakers` to 6
- **THEN** the campaign is created with `num_speakers` set to 6

#### Scenario: Create campaign with live transcription enabled
- **WHEN** the DM creates a campaign and enables the live transcription toggle
- **THEN** the campaign is created with `live_transcription` set to true

#### Scenario: Edit campaign live transcription setting
- **WHEN** the DM edits a campaign to enable or disable live transcription
- **THEN** the change is saved; future recordings in this campaign respect the updated setting

#### Scenario: Edit campaign speaker count
- **WHEN** the DM edits a campaign's `num_speakers` from 5 to 6
- **THEN** the change is saved; future diarization runs for this campaign use 6 speakers

#### Scenario: Speaker count validation
- **WHEN** the DM attempts to set `num_speakers` to 0 or 15
- **THEN** the form prevents submission and shows a validation error indicating the value must be between 1 and 10

#### Scenario: Existing campaigns get default
- **WHEN** the database is migrated to add the `live_transcription` column
- **THEN** all existing campaigns receive `live_transcription = false`

#### Scenario: Create campaign with empty name shows validation error
- **WHEN** the DM submits the campaign creation form with an empty name field
- **THEN** the name field is highlighted in red with the message "Campaign name is required" and the form is not submitted

#### Scenario: Edit campaign details
- **WHEN** the DM edits a campaign's name or description
- **THEN** the changes are saved and reflected everywhere the campaign is referenced

#### Scenario: Delete a campaign
- **WHEN** the DM deletes a campaign
- **THEN** a styled confirmation dialog appears with the warning "This will permanently delete this campaign and all its sessions, transcripts, and audio. This cannot be undone." and upon confirmation deletes the campaign
