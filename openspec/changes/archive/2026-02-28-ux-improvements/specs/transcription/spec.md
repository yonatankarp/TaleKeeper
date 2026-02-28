## ADDED Requirements

### Requirement: Transcript search and filtering
The system SHALL provide a search bar above the transcript view that filters segments by text content or speaker name. The filter SHALL be case-insensitive and update in real-time as the DM types. The system MUST show a match count and a clear button when a search is active.

#### Scenario: Search transcript by keyword
- **WHEN** the DM types "dragon" in the transcript search bar
- **THEN** only transcript segments containing "dragon" (case-insensitive) are shown, with a count like "12 matches"

#### Scenario: Search by speaker name
- **WHEN** the DM types "Thorin" in the search bar
- **THEN** segments where the speaker is Thorin are shown

#### Scenario: Clear search
- **WHEN** the DM clicks the "Clear" button next to the search bar
- **THEN** the search is cleared and all segments are shown again

#### Scenario: No matches found
- **WHEN** the DM searches for a term that doesn't appear in any segment
- **THEN** the message "No matches found." is displayed

### Requirement: Transcript empty state guidance
The system SHALL display a helpful message when no transcript is available.

#### Scenario: No transcript available
- **WHEN** the DM views a session with no transcript and no active recording
- **THEN** the message "No transcript available. Start recording or retranscribe audio to generate one." is displayed
