## ADDED Requirements

### Requirement: Embedding-based speaker change detection within long segments
The system SHALL detect speaker change points within VAD segments longer than 2.0 seconds using embedding cosine distance. For each qualifying segment, the system SHALL extract WeSpeaker 256-dim embeddings at a fine stride (0.6s windows, 0.3s step), compute cosine distance between consecutive embeddings, and identify peaks in the distance signal that indicate speaker transitions. The system SHALL split the original segment at each detected change point, producing sub-segments that each contain predominantly single-speaker speech. Segments shorter than 2.0 seconds SHALL pass through unchanged.

#### Scenario: Long cross-talk segment is split at speaker changes
- **WHEN** VAD produces a 15-second segment containing rapid cross-talk between 3 speakers
- **THEN** the system extracts fine-stride embeddings, detects speaker change points via cosine distance peaks, and splits the segment into multiple sub-segments each predominantly containing one speaker's voice

#### Scenario: Short segment passes through unchanged
- **WHEN** VAD produces a 1.5-second segment containing a single speaker's utterance
- **THEN** the segment is passed to embedding extraction without change detection processing

#### Scenario: Segment at boundary length
- **WHEN** VAD produces a segment of exactly 2.0 seconds
- **THEN** the segment is passed through unchanged (change detection requires segments strictly longer than the threshold)

#### Scenario: No change points detected in long segment
- **WHEN** a 10-second VAD segment contains only one speaker (e.g., a monologue)
- **THEN** the cosine distance signal has no peaks above the threshold and the original segment is preserved as-is

### Requirement: Change detection peak detection parameters
The system SHALL use peak detection with a minimum cosine distance height of 0.4 and a minimum peak distance of 3 steps (approximately 0.9 seconds) between detected change points. Sub-segments produced by splitting MUST be at least 0.4 seconds long (matching the minimum embedding extraction duration).

#### Scenario: Peaks below threshold are ignored
- **WHEN** a long segment has within-speaker pitch variation producing cosine distances of 0.2 between consecutive embeddings
- **THEN** no split points are detected and the segment passes through as-is

#### Scenario: Closely-spaced changes are filtered
- **WHEN** two speakers alternate with 0.5-second turns
- **THEN** the minimum peak distance filter prevents splitting into fragments shorter than ~0.9 seconds apart, preserving only the most prominent change points

#### Scenario: Sub-segments respect minimum duration
- **WHEN** a split would produce a sub-segment shorter than 0.4 seconds
- **THEN** the sub-segment is merged with its neighbor to ensure all output segments meet the minimum duration for embedding extraction

### Requirement: Change detection progress reporting
The system SHALL report progress during speaker change detection via the existing progress callback mechanism. The system SHALL emit a progress event when change detection begins and when it completes, including the number of segments processed and the number of change points detected.

#### Scenario: Change detection progress reported
- **WHEN** change detection processes 50 long VAD segments and finds 120 change points
- **THEN** the system emits progress events with detail "Detecting speaker changes..." at start and "Found 120 speaker changes in 50 segments" at completion

#### Scenario: Change detection skipped when no long segments exist
- **WHEN** all VAD segments are shorter than 2.0 seconds
- **THEN** the system skips change detection entirely and does not emit change detection progress events
