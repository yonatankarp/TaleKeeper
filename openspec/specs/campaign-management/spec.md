# Campaign Management

## Purpose

Provide full campaign and session lifecycle management, including CRUD operations for campaigns and sessions, session status tracking, player/character party management, and a campaign overview dashboard.

## Requirements

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

### Requirement: Session number backfill migration
The system SHALL backfill session numbers for existing sessions when the database is migrated. Sessions MUST be numbered sequentially per campaign, ordered by `created_at ASC, id ASC`, starting from each campaign's `session_start_number`.

#### Scenario: Migrate existing sessions
- **WHEN** the database migration runs on an existing database with sessions that have no `session_number`
- **THEN** each campaign's sessions are numbered sequentially starting from 0, ordered by creation date

#### Scenario: Backfill updates session names
- **WHEN** the backfill migration assigns session numbers
- **THEN** sessions whose name matches a generic pattern (empty or auto-generated) have their name updated to "Session N", while sessions with meaningful custom names are left unchanged

### Requirement: Session status tracking
The system SHALL track each session's status: `draft` (created, no recording), `recording` (actively recording), `transcribing` (processing audio), `completed` (transcription finished). Status MUST update automatically based on session activity.

#### Scenario: Status transitions
- **WHEN** a session is created
- **THEN** its status is `draft`
- **WHEN** the DM starts recording in that session
- **THEN** its status changes to `recording`
- **WHEN** the DM stops recording
- **THEN** its status changes to `transcribing` while the final transcription pass runs
- **WHEN** transcription completes
- **THEN** its status changes to `completed`

### Requirement: Player and character party
The system SHALL allow the DM to manage a party of players and their characters for each campaign. Each party entry MUST have a player name and character name. Party entries MAY be marked as active or inactive (for players who leave or join the campaign).

#### Scenario: Add a player to the party
- **WHEN** the DM adds a player "Alex" with character "Thorin Ironforge" to a campaign's party
- **THEN** the party entry is saved and available for speaker assignment in all sessions of that campaign

#### Scenario: Edit a party entry
- **WHEN** a player changes their character (e.g., character death) and the DM updates the character name from "Thorin" to "Lyra"
- **THEN** the party entry is updated; existing sessions retain the old character name in their speaker mappings, but new sessions use the updated name

#### Scenario: Mark player inactive
- **WHEN** a player leaves the campaign and the DM marks them as inactive
- **THEN** the player no longer appears in the default speaker assignment list for new sessions but remains visible in historical sessions

#### Scenario: Remove party entry
- **WHEN** the DM removes a party entry
- **THEN** a styled confirmation dialog appears with "Remove this player and character from the party?" and upon confirmation removes the entry

#### Scenario: Empty party shows guidance
- **WHEN** the DM opens a party page with no entries
- **THEN** the message "No players in the party yet. Add your party members above to use them for speaker identification." is displayed

### Requirement: Campaign overview dashboard
The system SHALL display a dashboard when opening a campaign showing session count, total recorded time, and the most recent session's date. The dashboard MUST provide quick access to start a new session or continue the most recent one.

#### Scenario: View campaign dashboard
- **WHEN** the DM opens a campaign that has 12 sessions with 36 hours of total recorded audio
- **THEN** the dashboard shows "12 sessions", "36h recorded", the date of the last session, and buttons to "Continue Last Session" and "New Session"

#### Scenario: Empty campaign dashboard
- **WHEN** the DM opens a newly created campaign with no sessions
- **THEN** the dashboard shows "0 sessions", a prominent "Start First Session" button, and the message "No sessions yet. Create a session to begin recording your next game."

#### Scenario: Session cards show context badges
- **WHEN** the DM views the session list on the campaign dashboard
- **THEN** each session card shows its status badge and, if audio exists, an "Audio" badge

### Requirement: Sidebar active page indicator
The system SHALL visually highlight the currently active campaign or page in the sidebar navigation. The active item MUST have a distinct left border and background color using the accent color.

#### Scenario: Active campaign highlighted
- **WHEN** the DM is viewing campaign "Curse of Strahd"
- **THEN** the "Curse of Strahd" item in the sidebar has an accent-colored left border and background highlight

#### Scenario: Settings page highlighted
- **WHEN** the DM is on the settings page
- **THEN** the "Settings" link in the sidebar is highlighted

#### Scenario: Child pages highlight parent campaign
- **WHEN** the DM is viewing a session or party within a campaign
- **THEN** the parent campaign is highlighted in the sidebar

### Requirement: Breadcrumb navigation
The system SHALL display a breadcrumb navigation trail at the top of the main content area on all pages except the campaign list. Each breadcrumb segment MUST be a clickable link for navigation.

#### Scenario: Session breadcrumbs
- **WHEN** the DM is viewing Session 12 in the "Curse of Strahd" campaign
- **THEN** breadcrumbs show "Campaigns / Curse of Strahd / Session 12" where "Campaigns" and "Curse of Strahd" are clickable links

#### Scenario: Party breadcrumbs
- **WHEN** the DM is viewing the party of a campaign
- **THEN** breadcrumbs show "Campaigns / [Campaign Name] / Party"

### Requirement: Campaign list empty state
The system SHALL display a helpful guidance message when the campaign list is empty.

#### Scenario: No campaigns exist
- **WHEN** the DM has no campaigns
- **THEN** the message "No campaigns yet. Create your first campaign to start recording sessions." is displayed

### Requirement: OS theme detection
The system SHALL detect the operating system's color scheme preference when no user theme preference is stored. The detected preference SHALL be used as the initial theme. User's explicit theme choice MUST take priority over OS detection.

#### Scenario: OS prefers light mode
- **WHEN** the DM opens TaleKeeper for the first time on a system set to light mode
- **THEN** the app renders in light theme

#### Scenario: Stored preference overrides OS
- **WHEN** the DM has previously selected dark mode but the OS is set to light mode
- **THEN** the app renders in dark theme (user preference wins)

### Requirement: Form validation for required fields
The system SHALL validate that required name fields are filled before submitting campaign and session creation forms. Empty required fields MUST be highlighted with a red border and an inline error message.

#### Scenario: Campaign name required
- **WHEN** the DM clicks "Create" on the campaign form with an empty name
- **THEN** the name input shows a red border and "Campaign name is required" message

#### Scenario: Session name required
- **WHEN** the DM clicks "Create" on the session form with an empty name
- **THEN** the name input shows a red border and "Session name is required" message
