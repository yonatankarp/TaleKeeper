## ADDED Requirements

### Requirement: Tab switching preserves running processes
The session detail view SHALL keep all tab content components mounted when switching between tabs. Inactive tabs SHALL be hidden visually but remain alive in the DOM so that running processes (recording, WebSocket connections, timers) are not interrupted.

#### Scenario: Recording continues when switching to transcript tab
- **WHEN** user is actively recording on the recording tab and switches to the transcript tab
- **THEN** the recording process (MediaRecorder, WebSocket, timer) SHALL continue running uninterrupted

#### Scenario: Switching back to a tab preserves its state
- **WHEN** user switches away from a tab and then switches back
- **THEN** the tab content SHALL be in the same state as when the user left (no re-mount, no data re-fetch, scroll position preserved)
