## MODIFIED Requirements

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

## RENAMED Requirements

### Requirement: Tab labels use D&D-themed terminology
- **FROM:** Tab labels "Transcript" and "Summaries"
- **TO:** Tab labels "Chronicle" and "Tales"
