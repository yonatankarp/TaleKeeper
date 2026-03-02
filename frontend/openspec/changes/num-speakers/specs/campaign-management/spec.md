# Campaign Management (Delta)

## MODIFIED Requirements

### Requirement: Campaign CRUD
The system SHALL allow the DM to create, view, edit, and delete campaigns. Each campaign MUST have a name and MAY have an optional description. Each campaign MUST have a `num_speakers` field (integer, default 5, range 2-10) representing the expected number of speakers at the table (DM + players).

#### Scenario: Create a campaign
- **WHEN** the DM creates a new campaign with the name "Curse of Strahd"
- **THEN** the campaign is created with `num_speakers` set to the default value of 5, appears in the campaign list, and is available for adding sessions

#### Scenario: Create campaign with custom speaker count
- **WHEN** the DM creates a new campaign with the name "Curse of Strahd" and sets num_speakers to 6
- **THEN** the campaign is created with `num_speakers` set to 6

#### Scenario: Create campaign with empty name shows validation error
- **WHEN** the DM submits the campaign creation form with an empty name field
- **THEN** the name field is highlighted in red with the message "Campaign name is required" and the form is not submitted

#### Scenario: Edit campaign details
- **WHEN** the DM edits a campaign's name, description, or num_speakers
- **THEN** the changes are saved and reflected everywhere the campaign is referenced

#### Scenario: Edit campaign speaker count
- **WHEN** the DM changes a campaign's num_speakers from 4 to 6
- **THEN** subsequent audio processing in that campaign's sessions SHALL use 6 as the expected speaker count for diarization

#### Scenario: Invalid speaker count rejected
- **WHEN** the DM attempts to set num_speakers to 1 or a value greater than 10
- **THEN** the system rejects the change with a validation error

#### Scenario: Delete a campaign
- **WHEN** the DM deletes a campaign
- **THEN** a styled confirmation dialog appears with the warning "This will permanently delete this campaign and all its sessions, transcripts, and audio. This cannot be undone." and upon confirmation deletes the campaign
