## MODIFIED Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically detect and distinguish different speakers in the audio using a four-stage pipeline: voice activity detection (Silero VAD), speaker change detection within long segments (embedding cosine distance), speaker embedding extraction (WeSpeaker ResNet34-LM via ONNX Runtime, 256-dim), and spectral clustering. After VAD, the system SHALL run speaker change detection on segments longer than 2.0 seconds to split them at speaker transition points, producing finer-grained sub-segments before embedding extraction. When voice signatures exist for the session's campaign, the system SHALL run the full pipeline first, then match resulting speaker clusters against stored signatures using cosine similarity. When no signatures exist, the system SHALL use unsupervised spectral clustering. The system SHALL accept `num_speakers` as a direct clustering input that determines the exact number of clusters (not a post-hoc constraint). The system SHALL also accept `min_speakers` and `max_speakers` bounds for automatic speaker count estimation via GMM+BIC. Each detected speaker MUST be assigned a provisional label (e.g., "Player 1", "Player 2") or matched to a known roster entry name.

#### Scenario: Speakers detected with voice signatures
- **WHEN** a recording is processed and the campaign has voice signatures
- **THEN** the system runs the diarize pipeline (VAD → change detection → embeddings → spectral clustering), computes per-speaker centroids, matches centroids against stored signatures via cosine similarity, and labels transcript segments with matched roster entry names or "Unknown Speaker"

#### Scenario: Speakers detected without voice signatures (cold start)
- **WHEN** a recording is processed and the campaign has no voice signatures
- **THEN** the system runs the diarize pipeline with change detection and spectral clustering and labels transcript segments with provisional identifiers (e.g., "Player 1", "Player 2")

#### Scenario: Speakers detected during recording
- **WHEN** a recording is in progress with multiple people speaking
- **THEN** the system detects distinct speakers and labels transcript segments with provisional speaker identifiers (e.g., "Speaker 1", "Speaker 2")

#### Scenario: Single speaker detected
- **WHEN** only one person has spoken during the recording
- **THEN** all transcript segments are assigned to "Player 1" or the matched roster entry name

#### Scenario: Final diarization uses campaign speaker count
- **WHEN** a recording is stopped in a campaign with `num_speakers` set to 5
- **THEN** the final diarization pass uses spectral clustering with exactly 5 clusters

#### Scenario: Speaker count fetched from campaign
- **WHEN** `run_final_diarization` is called for a session
- **THEN** the system looks up the session's campaign and retrieves its `num_speakers` value, passing it as `num_speakers` to spectral clustering

#### Scenario: Single speaker campaign
- **WHEN** a campaign has `num_speakers` set to 1
- **THEN** all transcript segments are assigned to a single speaker

#### Scenario: Retranscribe with speaker count override
- **WHEN** the user retranscribes a session with `num_speakers` set to 3
- **THEN** the final diarization pass uses spectral clustering with exactly 3 clusters, regardless of the campaign's default

#### Scenario: Recording with speaker count override
- **WHEN** the user sets `num_speakers` to 4 before recording
- **THEN** the final diarization after recording stop uses 4 clusters, regardless of the campaign's default

#### Scenario: Chunk diarization unchanged
- **WHEN** real-time chunk diarization runs during recording
- **THEN** it continues to use its existing approach (speaker change detection only affects the final pass)

#### Scenario: Cross-talk segments are sub-segmented before clustering
- **WHEN** VAD produces long segments containing rapid cross-talk between multiple speakers
- **THEN** the change detection stage splits these into finer sub-segments before embedding extraction, improving the quality of embeddings fed into spectral clustering
