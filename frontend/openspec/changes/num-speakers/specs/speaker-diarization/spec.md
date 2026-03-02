# Speaker Diarization (Delta)

## MODIFIED Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically detect and distinguish different speakers in the audio. When voice signatures exist for the session's campaign, the system SHALL use signature-based nearest-neighbor matching as the primary identification method. When no signatures exist, the system SHALL use the campaign's `num_speakers` setting to perform fixed-count agglomerative clustering, producing exactly the specified number of speaker clusters. Each detected speaker MUST be assigned a provisional label (e.g., "Player 1", "Player 2") or matched to a known roster entry name.

#### Scenario: Speakers detected with known count
- **WHEN** a recording is processed and the campaign has `num_speakers` set to 5 and no voice signatures
- **THEN** the system clusters audio into exactly 5 speaker groups and labels transcript segments with provisional identifiers ("Player 1" through "Player 5")

#### Scenario: Speakers detected with voice signatures
- **WHEN** a recording is processed and the campaign has voice signatures
- **THEN** the system matches audio windows against stored signatures regardless of the `num_speakers` setting

#### Scenario: Single speaker detected
- **WHEN** only one person has spoken during the recording and the campaign has `num_speakers` set to 1
- **THEN** all transcript segments are assigned to "Player 1" or the matched roster entry name
