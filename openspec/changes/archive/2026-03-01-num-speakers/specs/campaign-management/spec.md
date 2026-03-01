# Campaign Management (Delta)

## MODIFIED Requirements

### Requirement: Campaign CRUD
The system SHALL allow the DM to create, view, edit, and delete campaigns. Each campaign MUST have a name, MAY have an optional description, and MUST have a `num_speakers` field (integer, 1–10, default 5) indicating how many speakers to expect during diarization.

#### Scenario: Create a campaign
- **WHEN** the DM creates a new campaign with the name "Curse of Strahd"
- **THEN** the campaign is created with `num_speakers` defaulting to 5, appears in the campaign list, and is available for adding sessions

#### Scenario: Create campaign with custom speaker count
- **WHEN** the DM creates a campaign and sets `num_speakers` to 6
- **THEN** the campaign is created with `num_speakers` set to 6

#### Scenario: Edit campaign speaker count
- **WHEN** the DM edits a campaign's `num_speakers` from 5 to 6
- **THEN** the change is saved; future diarization runs for this campaign use 6 speakers

#### Scenario: Speaker count validation
- **WHEN** the DM attempts to set `num_speakers` to 0 or 15
- **THEN** the form prevents submission and shows a validation error indicating the value must be between 1 and 10

#### Scenario: Existing campaigns get default
- **WHEN** the database is migrated to add the `num_speakers` column
- **THEN** all existing campaigns receive `num_speakers = 5`
