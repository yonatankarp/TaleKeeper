## ADDED Requirements

### Requirement: Per-segment audio normalization before embedding extraction
The system SHALL normalize each audio segment to a consistent RMS level before extracting WeSpeaker embeddings. The normalization SHALL scale the segment's amplitude so that its RMS equals a target level of 0.1 (approximately -20 dBFS for float32 audio). The normalized audio SHALL be clipped to the [-1.0, 1.0] range to prevent overflow. Segments with RMS below 1e-6 (near-silence) SHALL skip normalization to avoid amplifying noise. The normalization SHALL apply to both the main embedding extraction path and the fine-stride embedding extraction used by speaker change detection.

#### Scenario: Quiet speaker segment is normalized
- **WHEN** an audio segment from a speaker far from the microphone has an RMS of 0.01
- **THEN** the system scales the segment by 10x to reach the target RMS of 0.1 before extracting the WeSpeaker embedding

#### Scenario: Loud speaker segment is normalized
- **WHEN** an audio segment from a speaker close to the microphone has an RMS of 0.3
- **THEN** the system scales the segment down to reach the target RMS of 0.1 before extracting the WeSpeaker embedding

#### Scenario: Near-silent segment skips normalization
- **WHEN** an audio segment has an RMS below 1e-6 (effectively silence or near-silence)
- **THEN** the system passes the segment through without normalization to avoid amplifying noise

#### Scenario: Normalized audio is clipped to valid range
- **WHEN** scaling a segment to the target RMS would produce sample values outside [-1.0, 1.0]
- **THEN** the system clips the audio to [-1.0, 1.0] after scaling to prevent clipping artifacts in the WAV file

#### Scenario: Fine-stride embeddings are also normalized
- **WHEN** the speaker change detection stage extracts fine-stride embeddings from a long segment
- **THEN** each fine-stride window is RMS-normalized before embedding extraction, consistent with the main extraction path
