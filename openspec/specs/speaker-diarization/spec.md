# Speaker Diarization

## Purpose

Provide automatic speaker detection and identification using a three-stage pipeline (Silero VAD, WeSpeaker embeddings, spectral clustering), aligning speakers with transcript segments, supporting real-time provisional labels during recording, and enabling manual speaker name assignment and correction.

## Requirements

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

### Requirement: Speaker-transcript alignment
The system SHALL align speaker diarization results with transcript segments so that each transcript segment is associated with exactly one speaker. When a single transcript segment contains speech from multiple speakers, it MUST be split at the speaker boundary. When using signature-based matching, speaker labels SHALL use the roster entry's player/character name directly instead of generic labels.

#### Scenario: Segments aligned with speakers
- **WHEN** diarization and transcription have both completed for a session
- **THEN** every transcript segment has exactly one speaker label and the speaker changes align with actual voice changes in the audio

#### Scenario: Segments aligned with known speakers
- **WHEN** diarization using voice signatures has completed for a session
- **THEN** every transcript segment has a speaker label matching a roster entry name, and the speaker changes align with actual voice changes in the audio

#### Scenario: Segments aligned with unknown speakers
- **WHEN** diarization has completed and some segments could not be matched to any voice signature
- **THEN** those segments are labeled "Unknown Speaker" and the user can manually reassign them

### Requirement: Near-real-time diarization during recording
The system SHALL run diarization on buffered audio chunks during recording and send provisional speaker labels to the frontend. Speaker labels MAY change as more audio context becomes available.

#### Scenario: Provisional labels during recording
- **WHEN** the DM is recording and two different people have spoken
- **THEN** transcript segments in the live view show different provisional speaker labels, which may be refined as more audio is processed

#### Scenario: Labels stabilize after recording ends
- **WHEN** a recording is stopped
- **THEN** the system runs a final diarization pass on the complete audio to produce stable, consistent speaker labels across the entire session

### Requirement: Manual speaker name assignment
The system SHALL allow the DM to assign player names and character names to all detected speakers in a single batch operation. The speaker panel MUST show all speakers simultaneously with input fields for player name and character name, roster quick-select buttons, a single "Save All" button that updates all speakers at once, and a "Merge into..." action per speaker for combining duplicate speakers. The assignment MUST update all transcript segments for each speaker in the session. The speaker list MAY shrink after user-initiated merges, reflecting that two detected speakers were the same person.

#### Scenario: Batch assign all speakers
- **WHEN** the DM clicks "Edit All" on the speaker panel with 4 detected speakers
- **THEN** a form appears showing all 4 speakers with their diarization labels, input fields for player name and character name, roster suggestion buttons, and a "Merge into..." action for each

#### Scenario: Save all speaker assignments at once
- **WHEN** the DM has filled in names for all speakers and clicks "Save All"
- **THEN** all speaker assignments are saved and all transcript segments are updated to reflect the new names

#### Scenario: Roster quick-select in batch mode
- **WHEN** the DM clicks a roster suggestion button next to a speaker in batch edit mode
- **THEN** that speaker's player name and character name fields are populated with the roster entry's values

#### Scenario: Cancel batch edit
- **WHEN** the DM clicks "Cancel" during batch editing
- **THEN** all edits are discarded and the speaker panel returns to its read-only view

#### Scenario: Speaker count reduced after merge
- **WHEN** the DM merges "Player 3" into "Player 1" in a session that originally had 4 detected speakers
- **THEN** the speaker panel shows 3 speakers and all transcript segments formerly attributed to "Player 3" now appear under "Player 1"

### Requirement: Speaker reassignment correction
The system SHALL allow the DM to reassign individual transcript segments to a different speaker. This corrects diarization errors without changing the global speaker mapping.

#### Scenario: Reassign a mislabeled segment
- **WHEN** a transcript segment is attributed to "Thorin" but the DM knows it was spoken by "Elara"
- **THEN** the DM can select that segment and reassign it to "Elara", updating only that segment's speaker association

#### Scenario: Bulk reassign segments
- **WHEN** the DM selects multiple consecutive transcript segments
- **THEN** the DM can reassign all selected segments to a different speaker in a single action

### Requirement: Speaker list from campaign roster
The system SHALL pre-populate the speaker name assignment UI with player and character names from the campaign's roster, if the session belongs to a campaign with a configured roster.

#### Scenario: Roster names available for assignment
- **WHEN** the DM opens speaker assignment for a session in a campaign with 5 players configured
- **THEN** the assignment dropdown shows all 5 player/character name pairs from the roster, plus an option to add a new speaker (e.g., for NPCs or guests)
