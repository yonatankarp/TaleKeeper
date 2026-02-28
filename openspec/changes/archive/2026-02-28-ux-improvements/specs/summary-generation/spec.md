## MODIFIED Requirements

### Requirement: Summary regeneration
The system SHALL allow the DM to regenerate summaries for a session, replacing the previous summaries. The system MUST display a styled confirmation dialog before overwriting existing summaries. During generation, the system MUST show a spinner with elapsed time counter.

#### Scenario: Regenerate with confirmation dialog
- **WHEN** the DM clicks "Regenerate" on a session that already has summaries
- **THEN** a styled confirmation dialog appears with the message "This will replace existing [type] summaries with newly generated ones." and Regenerate/Cancel buttons

#### Scenario: Generation progress with elapsed time
- **WHEN** summary generation is in progress
- **THEN** the generate buttons show a spinner icon and elapsed time counter (e.g., "Generating... (12s)")

#### Scenario: Generation completes
- **WHEN** summary generation finishes
- **THEN** the spinner and timer stop, and the new summary is displayed

### Requirement: Summary editing
The system SHALL allow the DM to manually edit generated summaries before exporting or sharing. Edits MUST be saved and persist across application restarts.

#### Scenario: Edit a generated summary
- **WHEN** the DM edits the text of a generated session summary
- **THEN** the changes are saved to the database and displayed on subsequent views

#### Scenario: Delete summary with styled dialog
- **WHEN** the DM clicks "Delete" on a summary
- **THEN** a styled confirmation dialog appears with "Are you sure you want to delete this summary?" and upon confirmation removes the summary

## ADDED Requirements

### Requirement: Summary empty state guidance
The system SHALL display a helpful message when no summaries have been generated.

#### Scenario: No summaries yet
- **WHEN** the DM views the summaries tab with no generated summaries
- **THEN** the message "No summaries generated yet. Generate a summary after your session is transcribed." is displayed
