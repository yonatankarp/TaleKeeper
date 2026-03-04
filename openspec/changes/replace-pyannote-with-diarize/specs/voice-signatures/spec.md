## MODIFIED Requirements

### Requirement: Voice signature extraction from labeled sessions
The system SHALL extract voice signatures from sessions where speakers have been manually assigned to campaign roster entries. For each roster-linked speaker, the system SHALL compute an averaged, L2-normalized 256-dimensional embedding from all transcript segments assigned to that speaker using the WeSpeaker ResNet34-LM model via ONNX Runtime. The extraction SHALL use VAD to identify speech segments, extract windowed embeddings (1.2s windows, 0.6s step), filter to subsegments overlapping the speaker's transcript time ranges, and average the results.

#### Scenario: Extract signatures from a fully labeled session
- **WHEN** a session has audio, transcript segments, and at least one speaker assigned to a roster entry, and the user triggers "Generate Voice Signatures"
- **THEN** the system runs VAD on the audio, extracts 256-dim WeSpeaker embeddings from subsegments overlapping each labeled speaker's transcript ranges, averages them into one embedding per speaker, L2-normalizes it, and stores it as a voice signature linked to the roster entry

#### Scenario: Partial labeling
- **WHEN** a session has 4 detected speakers but only 2 are assigned to roster entries
- **THEN** the system generates voice signatures only for the 2 assigned speakers and ignores the unassigned ones

#### Scenario: Regenerate existing signature
- **WHEN** a roster entry already has a voice signature and the user generates signatures from a new session
- **THEN** the existing signature for that roster entry is replaced with the new one extracted from the current session

### Requirement: Signature-based speaker matching during diarization
The system SHALL use stored voice signatures as a post-clustering identification method when signatures exist for the session's campaign. The system SHALL first run the full diarize pipeline (VAD → embeddings → spectral clustering) to produce speaker clusters, then compute an L2-normalized centroid embedding for each cluster, then compare each centroid against all campaign voice signatures using cosine similarity. A speaker cluster SHALL be matched to the closest signature above the campaign's `similarity_threshold` (default 0.75 for new campaigns). Unmatched clusters SHALL be labeled "Unknown Speaker".

#### Scenario: Diarization with signatures available
- **WHEN** a session is diarized and the campaign has voice signatures for 4 roster entries
- **THEN** the system runs the full diarize pipeline, computes per-cluster centroids, compares each centroid against all 4 signatures, and assigns matched roster entry names to clusters above the similarity threshold

#### Scenario: Audio window below similarity threshold
- **WHEN** a speaker cluster's centroid has a highest cosine similarity below the campaign's similarity threshold to any stored signature
- **THEN** that cluster is labeled "Unknown Speaker"

#### Scenario: Fallback to clustering when no signatures exist
- **WHEN** a session is diarized and the campaign has no voice signatures
- **THEN** the system uses unsupervised spectral clustering only

#### Scenario: Default similarity threshold for new campaigns
- **WHEN** a new campaign is created
- **THEN** its similarity_threshold defaults to 0.75

## ADDED Requirements

### Requirement: No HuggingFace token required for voice signature extraction
The system SHALL NOT require a HuggingFace token for extracting voice signatures. The WeSpeaker ResNet34-LM model SHALL download automatically via ONNX Runtime without authentication.

#### Scenario: Voice signature generation without HF token
- **WHEN** the user generates voice signatures and no HuggingFace token is configured
- **THEN** voice signature extraction completes successfully using the auto-downloaded WeSpeaker model
