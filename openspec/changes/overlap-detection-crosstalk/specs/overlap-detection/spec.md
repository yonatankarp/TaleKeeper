## ADDED Requirements

### Requirement: Post-clustering overlap detection
After spectral clustering, the system SHALL identify subsegments whose embeddings are geometrically ambiguous between two or more speaker clusters. A subsegment is considered overlapping when the cosine similarity to its second-nearest cluster centroid divided by the cosine similarity to its nearest centroid meets or exceeds `OVERLAP_RATIO_THRESHOLD` (default 0.85). Detected overlap subsegments MUST be assigned the special label `[crosstalk]` instead of any speaker label. The detection SHALL run in both the unsigned (`diarize`) and signature-matched (`diarize_with_signatures`) diarization paths.

#### Scenario: Ambiguous embedding flagged as crosstalk
- **WHEN** a subsegment embedding sits nearly equidistant between two cluster centroids (similarity ratio >= 0.85)
- **THEN** that subsegment is assigned the label `[crosstalk]` and is not attributed to any single speaker

#### Scenario: Clear single-speaker embedding not flagged
- **WHEN** a subsegment embedding sits firmly within one cluster (similarity to second-nearest centroid is well below threshold)
- **THEN** that subsegment is attributed to its assigned speaker and not flagged as overlap

#### Scenario: Overlap detection runs in both diarization paths
- **WHEN** diarization completes (with or without voice signatures)
- **THEN** the overlap detection step runs before segment assembly in both cases

#### Scenario: Single-speaker session produces no crosstalk
- **WHEN** a session has only one detected speaker cluster
- **THEN** no segments are flagged as `[crosstalk]` (ratio test requires at least two clusters)

### Requirement: Crosstalk excluded from speaker attribution
The system SHALL NOT attribute `[crosstalk]` segments to any speaker. These segments MUST be stored with `is_overlap = 1` and `speaker_id = NULL` in the `transcript_segments` table. Overlap time MUST be excluded from per-speaker speaking time totals shown in the speaker panel.

#### Scenario: Crosstalk segment has no speaker
- **WHEN** a transcript segment is aligned to a `[crosstalk]` diarization segment
- **THEN** that transcript segment has `speaker_id = NULL` and `is_overlap = 1` in the database

#### Scenario: Speaker panel excludes overlap time
- **WHEN** the speaker panel displays per-speaker speaking totals for a session containing crosstalk segments
- **THEN** the totals reflect only segments attributed to that speaker, not the crosstalk time

### Requirement: Crosstalk visual treatment in transcript
The system SHALL render `[crosstalk]` transcript segments distinctly in the transcript view. These segments MUST be visually differentiated from speaker-attributed segments (e.g., muted color, italicised label) and MUST display the label "[crosstalk]" rather than a speaker name.

#### Scenario: Crosstalk displayed in transcript
- **WHEN** the DM views the transcript tab for a session containing overlap segments
- **THEN** those segments appear with a muted style and the label "[crosstalk]" instead of a player name

#### Scenario: Crosstalk excluded from speaker filter
- **WHEN** the DM filters the transcript by a specific speaker name
- **THEN** `[crosstalk]` segments are not shown in the filtered results
