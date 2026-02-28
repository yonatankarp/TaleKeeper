## MODIFIED Requirements

### Requirement: Player and character roster
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

### Requirement: Breadcrumb navigation
The system SHALL display a breadcrumb navigation trail at the top of the main content area on all pages except the campaign list. Each breadcrumb segment MUST be a clickable link for navigation.

#### Scenario: Session breadcrumbs
- **WHEN** the DM is viewing Session 12 in the "Curse of Strahd" campaign
- **THEN** breadcrumbs show "Campaigns / Curse of Strahd / Session 12" where "Campaigns" and "Curse of Strahd" are clickable links

#### Scenario: Party breadcrumbs
- **WHEN** the DM is viewing the party of a campaign
- **THEN** breadcrumbs show "Campaigns / [Campaign Name] / Party"
