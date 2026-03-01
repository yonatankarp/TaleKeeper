# Speaker Diarization (Delta)

## MODIFIED Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically detect and distinguish different speakers in the audio. When voice signatures exist for the session's campaign, the system SHALL use signature-based nearest-neighbor matching as the primary identification method. When no signatures exist, the system SHALL fall back to unsupervised agglomerative clustering with tuned parameters (3-second windows, 1.5-second hop, cosine distance threshold of 1.0). Each detected speaker MUST be assigned a provisional label (e.g., "Player 1", "Player 2") or matched to a known roster entry name.

#### Scenario: Speakers detected with voice signatures
- **WHEN** a recording is processed and the campaign has voice signatures
- **THEN** the system matches audio windows against stored signatures and labels transcript segments with the matched roster entry names

#### Scenario: Speakers detected without voice signatures (cold start)
- **WHEN** a recording is processed and the campaign has no voice signatures
- **THEN** the system uses unsupervised clustering with tuned parameters and labels transcript segments with provisional identifiers (e.g., "Player 1", "Player 2")

#### Scenario: Single speaker detected
- **WHEN** only one person has spoken during the recording
- **THEN** all transcript segments are assigned to "Player 1" or the matched roster entry name

### Requirement: Speaker-transcript alignment
The system SHALL align speaker diarization results with transcript segments so that each transcript segment is associated with exactly one speaker. When a single transcript segment contains speech from multiple speakers, it MUST be split at the speaker boundary. When using signature-based matching, speaker labels SHALL use the roster entry's player/character name directly instead of generic labels.

#### Scenario: Segments aligned with known speakers
- **WHEN** diarization using voice signatures has completed for a session
- **THEN** every transcript segment has a speaker label matching a roster entry name, and the speaker changes align with actual voice changes in the audio

#### Scenario: Segments aligned with unknown speakers
- **WHEN** diarization has completed and some segments could not be matched to any voice signature
- **THEN** those segments are labeled "Unknown Speaker" and the user can manually reassign them
