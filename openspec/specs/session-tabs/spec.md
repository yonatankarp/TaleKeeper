# Capability: Session Tabs

## Purpose
Manage tab-based navigation within the session detail view, ensuring that switching between tabs does not disrupt active processes or lose component state.

## Requirements

### Requirement: Tab switching preserves running processes
The session detail view SHALL keep all tab content components mounted when switching between tabs. Inactive tabs SHALL be hidden visually but remain alive in the DOM so that running processes (recording, WebSocket connections, timers) are not interrupted.

#### Scenario: Recording continues when switching to transcript tab
- **WHEN** user is actively recording on the recording tab and switches to the transcript tab
- **THEN** the recording process (MediaRecorder, WebSocket, timer) SHALL continue running uninterrupted

#### Scenario: Switching back to a tab preserves its state
- **WHEN** user switches away from a tab and then switches back
- **THEN** the tab content SHALL be in the same state as when the user left (no re-mount, no data re-fetch, scroll position preserved)

### Requirement: Recording status badge in session header
The session detail view SHALL display a persistent recording status badge in the page header when a recording is active or paused. The badge MUST be visible regardless of which tab is active. The badge MUST show a pulsing amber-red dot (when recording) or static dot (when paused), the elapsed time, and a state label (REC/PAUSED).

#### Scenario: Recording badge visible on Chronicle tab
- **WHEN** the DM is recording on the Recording tab and switches to the Chronicle tab
- **THEN** the recording badge in the session header continues showing the pulsing amber-red dot and incrementing elapsed time

#### Scenario: Badge shows paused state
- **WHEN** the DM pauses a recording and switches to the Tales tab
- **THEN** the badge shows a static amber-red dot, frozen elapsed time, and "PAUSED" label

#### Scenario: Badge disappears when recording stops
- **WHEN** the DM stops a recording
- **THEN** the recording badge is no longer visible in the session header

### Requirement: Tab labels use D&D-themed terminology
The session detail view SHALL use D&D-themed names for its tab labels. The tab previously labeled "Transcript" SHALL be labeled "Chronicle". The tab previously labeled "Summaries" SHALL be labeled "Tales".
