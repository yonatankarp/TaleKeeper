## ADDED Requirements

### Requirement: LLM-based session name generation
The system SHALL generate a short, catchy session title from the transcript content using the configured LLM provider. The generated title MUST be 2–6 words that capture the session's key theme or event. The system SHALL use a sampling strategy, sending the first ~2000 and last ~2000 characters of the formatted transcript to the LLM prompt.

#### Scenario: Name generated after transcription completes
- **WHEN** a session's transcription and diarization finish (status transitions to `completed`)
- **AND** the session name matches the auto-assigned "Session N" pattern (user has not customized it)
- **THEN** the system calls the LLM to generate a catchy title and updates the session name to "Session N: Generated Title"

#### Scenario: Name generation with short transcript
- **WHEN** the transcript is shorter than 4000 characters total
- **THEN** the system sends the full transcript to the LLM without sampling

#### Scenario: User has customized the session name
- **WHEN** transcription completes but the session name does not match the "Session N" pattern (the user renamed it)
- **THEN** the system SHALL NOT overwrite the custom name with an LLM-generated one

#### Scenario: LLM unavailable during name generation
- **WHEN** transcription completes and the LLM provider is unreachable or returns an error
- **THEN** the session keeps its existing "Session N" name and no error is surfaced to the user

#### Scenario: Name generation does not block processing
- **WHEN** the processing pipeline (transcription + diarization) completes
- **THEN** the "done" event is emitted to the frontend immediately, and name generation runs as a background task afterward

### Requirement: Manual session name editing
The system SHALL allow the DM to edit the session name at any time after creation. An edited name MUST persist and MUST NOT be overwritten by subsequent LLM name generation.

#### Scenario: Edit auto-generated name
- **WHEN** the DM edits a session named "Session 3: The Dragon's Lair" to "Session 3: Into the Dragon's Den"
- **THEN** the updated name is saved and displayed everywhere

#### Scenario: Edit preserves against regeneration
- **WHEN** the DM has edited the session name to a custom value
- **AND** a re-transcription triggers name generation
- **THEN** the custom name is preserved because it no longer matches the "Session N" pattern

### Requirement: Session name generation endpoint
The system SHALL expose an API endpoint to manually trigger session name generation. This allows the DM to regenerate a title if the automatic one was unsatisfactory.

#### Scenario: Manual name regeneration
- **WHEN** the DM triggers name regeneration for a completed session via the API
- **THEN** the system generates a new title from the transcript and updates the session name to "Session N: New Title", regardless of the current name

#### Scenario: Regeneration for session without transcript
- **WHEN** the DM triggers name regeneration for a session with no transcript segments
- **THEN** the system returns an error indicating that a transcript is required for name generation
