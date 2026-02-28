## ADDED Requirements

### Requirement: Campaign CRUD
The system SHALL allow the DM to create, view, edit, and delete campaigns. Each campaign MUST have a name and MAY have an optional description.

#### Scenario: Create a campaign
- **WHEN** the DM creates a new campaign with the name "Curse of Strahd"
- **THEN** the campaign is created, appears in the campaign list, and is available for adding sessions

#### Scenario: Edit campaign details
- **WHEN** the DM edits a campaign's name or description
- **THEN** the changes are saved and reflected everywhere the campaign is referenced

#### Scenario: Delete a campaign
- **WHEN** the DM deletes a campaign
- **THEN** the system prompts for confirmation, and upon confirmation deletes the campaign along with all its sessions, transcripts, summaries, and audio files

### Requirement: Session CRUD within campaigns
The system SHALL allow the DM to create, view, edit, and delete sessions within a campaign. Each session MUST have a name and date. Sessions MUST be listed in chronological order within their campaign.

#### Scenario: Create a session
- **WHEN** the DM creates a new session in a campaign with name "Session 12 - The Dark Forest" and today's date
- **THEN** the session is created within the campaign and appears in the session list ordered by date

#### Scenario: View session list
- **WHEN** the DM opens a campaign
- **THEN** all sessions are listed in chronological order (newest first) showing name, date, and status (recording, completed, or no recording)

#### Scenario: Delete a session
- **WHEN** the DM deletes a session
- **THEN** the system prompts for confirmation, and upon confirmation deletes the session along with its audio, transcript, and summaries

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

### Requirement: Player and character roster
The system SHALL allow the DM to manage a roster of players and their characters for each campaign. Each roster entry MUST have a player name and character name. Roster entries MAY be marked as active or inactive (for players who leave or join the campaign).

#### Scenario: Add a player to the roster
- **WHEN** the DM adds a player "Alex" with character "Thorin Ironforge" to a campaign's roster
- **THEN** the roster entry is saved and available for speaker assignment in all sessions of that campaign

#### Scenario: Edit a roster entry
- **WHEN** a player changes their character (e.g., character death) and the DM updates the character name from "Thorin" to "Lyra"
- **THEN** the roster entry is updated; existing sessions retain the old character name in their speaker mappings, but new sessions use the updated name

#### Scenario: Mark player inactive
- **WHEN** a player leaves the campaign and the DM marks them as inactive
- **THEN** the player no longer appears in the default speaker assignment list for new sessions but remains visible in historical sessions

### Requirement: Campaign overview dashboard
The system SHALL display a dashboard when opening a campaign showing session count, total recorded time, and the most recent session's date. The dashboard MUST provide quick access to start a new session or continue the most recent one.

#### Scenario: View campaign dashboard
- **WHEN** the DM opens a campaign that has 12 sessions with 36 hours of total recorded audio
- **THEN** the dashboard shows "12 sessions", "36h recorded", the date of the last session, and buttons to "New Session" or "Continue Last Session"

#### Scenario: Empty campaign dashboard
- **WHEN** the DM opens a newly created campaign with no sessions
- **THEN** the dashboard shows "0 sessions" and a prominent "Start First Session" button
