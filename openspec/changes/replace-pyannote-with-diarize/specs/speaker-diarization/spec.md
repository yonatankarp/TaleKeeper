## MODIFIED Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically detect and distinguish different speakers in the audio using a three-stage pipeline: voice activity detection (Silero VAD), speaker embedding extraction (WeSpeaker ResNet34-LM via ONNX Runtime, 256-dim), and spectral clustering. When voice signatures exist for the session's campaign, the system SHALL run the full pipeline first, then match resulting speaker clusters against stored signatures using cosine similarity. When no signatures exist, the system SHALL use unsupervised spectral clustering. The system SHALL accept `num_speakers` as a direct clustering input that determines the exact number of clusters (not a post-hoc constraint). The system SHALL also accept `min_speakers` and `max_speakers` bounds for automatic speaker count estimation via GMM+BIC. Each detected speaker MUST be assigned a provisional label (e.g., "Player 1", "Player 2") or matched to a known roster entry name.

#### Scenario: Speakers detected with voice signatures
- **WHEN** a recording is processed and the campaign has voice signatures
- **THEN** the system runs the diarize pipeline (VAD → embeddings → spectral clustering), computes per-speaker centroids, matches centroids against stored signatures via cosine similarity, and labels transcript segments with matched roster entry names or "Unknown Speaker"

#### Scenario: Speakers detected without voice signatures (cold start)
- **WHEN** a recording is processed and the campaign has no voice signatures
- **THEN** the system runs the diarize pipeline with spectral clustering and labels transcript segments with provisional identifiers (e.g., "Player 1", "Player 2")

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
- **THEN** it continues to use its existing approach (the diarize library replacement only affects the final pass)

## ADDED Requirements

### Requirement: Per-stage diarization progress reporting
The system SHALL report progress at each stage of the diarization pipeline via SSE events. The system SHALL report VAD completion with the number of speech segments found, embedding extraction progress as X/Y per speech segment, and clustering completion with the number of speakers and segments found.

#### Scenario: VAD progress reported
- **WHEN** voice activity detection completes on a 2-hour audio file and finds 500 speech segments totaling 90 minutes of speech
- **THEN** the system emits an SSE progress event with detail "Found 500 speech segments (5400s of speech)"

#### Scenario: Embedding extraction progress reported
- **WHEN** the system is extracting speaker embeddings for 500 speech segments
- **THEN** the system emits SSE progress events at regular intervals with detail "Extracting speaker embeddings (250/500)..."

#### Scenario: Clustering progress reported
- **WHEN** spectral clustering completes and identifies 5 speakers across 300 segments
- **THEN** the system emits an SSE progress event with detail "Found 5 speakers, 300 segments"

#### Scenario: Diarization phase announced
- **WHEN** diarization begins
- **THEN** the system emits an SSE phase event with `{"phase": "diarization"}` and a progress event with detail "Detecting speech activity..."

### Requirement: No HuggingFace token required for diarization
The system SHALL NOT require a HuggingFace token for speaker diarization or embedding extraction. All models (Silero VAD, WeSpeaker ResNet34-LM) SHALL download automatically on first use without authentication.

#### Scenario: Diarization without HF token
- **WHEN** a session is processed and no HuggingFace token is configured
- **THEN** diarization completes successfully using auto-downloaded models

#### Scenario: First-time model download
- **WHEN** diarization runs for the first time on a fresh install
- **THEN** required models are downloaded automatically without user intervention

### Requirement: No GPU device targeting
The system SHALL run all diarization and embedding extraction on CPU. The system SHALL NOT target MPS, CUDA, or any GPU device for the diarize pipeline.

#### Scenario: Diarization runs on CPU
- **WHEN** diarization is invoked on a machine with an Apple Silicon GPU
- **THEN** all processing runs on CPU via ONNX Runtime and PyTorch CPU backend
