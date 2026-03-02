## MODIFIED Requirements

### Requirement: Session CRUD within campaigns
The system SHALL allow the DM to create, view, edit, and delete sessions within a campaign. Each session MUST have a name, date, and session number. The session number MUST be automatically assigned at creation time as the next sequential number within the campaign, starting from the campaign's configured `session_start_number` (default 0). Sessions MUST be listed in chronological order within their campaign. The auto-assigned session name MUST follow the format "Session N" where N is the session number.

#### Scenario: Create a session
- **WHEN** the DM creates a new session in a campaign that has no existing sessions and `session_start_number` is 0
- **THEN** the session is created with `session_number` = 0, name auto-set to "Session 0", and appears in the session list ordered by date

#### Scenario: Create session with existing sessions
- **WHEN** the DM creates a new session in a campaign that already has sessions numbered 0, 1, and 2
- **THEN** the session is created with `session_number` = 3 and name auto-set to "Session 3"

#### Scenario: Create session with custom start number
- **WHEN** the DM creates a new session in a campaign with `session_start_number` set to 5 and no existing sessions
- **THEN** the session is created with `session_number` = 5 and name auto-set to "Session 5"

#### Scenario: Create session with empty name uses auto-name
- **WHEN** the DM submits the session creation form without providing a name
- **THEN** the session is created with the auto-assigned "Session N" name

#### Scenario: Create session with custom name
- **WHEN** the DM submits the session creation form with a custom name "The Finale"
- **THEN** the session is created with that custom name and the correct `session_number`

#### Scenario: View session list
- **WHEN** the DM opens a campaign
- **THEN** all sessions are listed in chronological order (newest first) showing their name (which includes session number if auto-named), date, and status

#### Scenario: Delete a session
- **WHEN** the DM deletes a session
- **THEN** a styled confirmation dialog appears with the warning "This will delete this session and all its audio, transcript, and summaries." and upon confirmation deletes the session

#### Scenario: Deleted session does not affect numbering
- **WHEN** the DM deletes Session 2 from a campaign with sessions 0, 1, 2, 3
- **THEN** sessions 0, 1, 3 retain their original numbers, and the next created session is numbered 4

### Requirement: Campaign CRUD
The system SHALL allow the DM to create, view, edit, and delete campaigns. Each campaign MUST have a name, MAY have an optional description, MUST have a `num_speakers` field (integer, 1–10, default 5), and MUST have a `session_start_number` field (integer, default 0) indicating the number assigned to the first session.

#### Scenario: Create a campaign
- **WHEN** the DM creates a new campaign with the name "Curse of Strahd"
- **THEN** the campaign is created with `num_speakers` defaulting to 5 and `session_start_number` defaulting to 0, appears in the campaign list, and is available for adding sessions

#### Scenario: Create campaign with custom start number
- **WHEN** the DM creates a campaign and sets `session_start_number` to 5
- **THEN** the campaign is created with `session_start_number` set to 5, and the first session created in it will be numbered 5

#### Scenario: Edit campaign start number
- **WHEN** the DM edits a campaign's `session_start_number` from 0 to 10
- **THEN** the change is saved; existing sessions retain their numbers, but the next created session uses `MAX(existing session_number) + 1` (the start number only applies when no sessions exist yet)

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
- **WHEN** the database is migrated to add the `session_start_number` column
- **THEN** all existing campaigns receive `session_start_number = 0`

#### Scenario: Create campaign with empty name shows validation error
- **WHEN** the DM submits the campaign creation form with an empty name field
- **THEN** the name field is highlighted in red with the message "Campaign name is required" and the form is not submitted

#### Scenario: Edit campaign details
- **WHEN** the DM edits a campaign's name or description
- **THEN** the changes are saved and reflected everywhere the campaign is referenced

#### Scenario: Delete a campaign
- **WHEN** the DM deletes a campaign
- **THEN** a styled confirmation dialog appears with the warning "This will permanently delete this campaign and all its sessions, transcripts, and audio. This cannot be undone." and upon confirmation deletes the campaign

## ADDED Requirements

### Requirement: Session number backfill migration
The system SHALL backfill session numbers for existing sessions when the database is migrated. Sessions MUST be numbered sequentially per campaign, ordered by `created_at ASC, id ASC`, starting from each campaign's `session_start_number`.

#### Scenario: Migrate existing sessions
- **WHEN** the database migration runs on an existing database with sessions that have no `session_number`
- **THEN** each campaign's sessions are numbered sequentially starting from 0, ordered by creation date

#### Scenario: Backfill updates session names
- **WHEN** the backfill migration assigns session numbers
- **THEN** sessions whose name matches a generic pattern (empty or auto-generated) have their name updated to "Session N", while sessions with meaningful custom names are left unchanged
