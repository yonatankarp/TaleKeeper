# Speaker Diarization (Delta)

## MODIFIED Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically detect and distinguish different speakers in the audio. During final diarization, the system SHALL use the campaign's `num_speakers` setting to perform fixed-count agglomerative clustering instead of threshold-based automatic speaker count detection. Each detected speaker MUST be assigned a provisional label (e.g., "Speaker 1", "Speaker 2").

#### Scenario: Final diarization uses campaign speaker count
- **WHEN** a recording is stopped in a campaign with `num_speakers` set to 5
- **THEN** the final diarization pass clusters speaker embeddings into exactly 5 speaker groups

#### Scenario: Speaker count fetched from campaign
- **WHEN** `run_final_diarization` is called for a session
- **THEN** the system looks up the session's campaign and retrieves its `num_speakers` value, passing it to `_cluster_embeddings`

#### Scenario: Single speaker campaign
- **WHEN** a campaign has `num_speakers` set to 1
- **THEN** all transcript segments are assigned to a single speaker

#### Scenario: Retranscribe with speaker count override
- **WHEN** the user retranscribes a session with `num_speakers` set to 3
- **THEN** the final diarization pass clusters speaker embeddings into exactly 3 speakers, regardless of the campaign's default

#### Scenario: Recording with speaker count override
- **WHEN** the user sets `num_speakers` to 4 before recording
- **THEN** the final diarization after recording stop uses 4 speakers, regardless of the campaign's default

#### Scenario: Chunk diarization unchanged
- **WHEN** real-time chunk diarization runs during recording
- **THEN** it continues to use threshold-based clustering (the `num_speakers` setting only affects the final pass)
