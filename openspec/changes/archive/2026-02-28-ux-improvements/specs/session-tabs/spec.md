## ADDED Requirements

### Requirement: Recording status badge in session header
The session detail view SHALL display a persistent recording status badge in the page header when a recording is active or paused. The badge MUST be visible regardless of which tab is active. The badge MUST show a pulsing red dot (when recording) or static dot (when paused), the elapsed time, and a state label (REC/PAUSED).

#### Scenario: Recording badge visible on transcript tab
- **WHEN** the DM is recording on the Recording tab and switches to the Transcript tab
- **THEN** the recording badge in the session header continues showing the pulsing red dot and incrementing elapsed time

#### Scenario: Badge shows paused state
- **WHEN** the DM pauses a recording and switches to the Summaries tab
- **THEN** the badge shows a static red dot, frozen elapsed time, and "PAUSED" label

#### Scenario: Badge disappears when recording stops
- **WHEN** the DM stops a recording
- **THEN** the recording badge is no longer visible in the session header
