## ADDED Requirements

### Requirement: Optional source separation stage in diarization pipeline
When the session's campaign has `source_separation_enabled = true`, the diarization pipeline SHALL run source separation as stage 0, before AGC normalization and VAD. The separated streams SHALL be used as input to VAD and embedding extraction. When `source_separation_enabled = false`, the pipeline SHALL be identical to its current behaviour with no separation stage.

#### Scenario: Pipeline runs separation when enabled
- **WHEN** `diarize()` or `diarize_with_signatures()` is called for a session in a campaign with source separation enabled
- **THEN** `separate_audio()` is called first, its output streams are passed to VAD and embedding extraction, and separation temp files are cleaned up in a finally block

#### Scenario: Pipeline unchanged when separation disabled
- **WHEN** `diarize()` or `diarize_with_signatures()` is called for a session in a campaign with source separation disabled
- **THEN** the pipeline runs identically to pre-separation behaviour: AGC normalization → VAD → change detection → embeddings → clustering

#### Scenario: Both separated streams contribute embeddings to clustering
- **WHEN** source separation produces 2 streams and embedding extraction runs on both
- **THEN** embeddings from both streams are pooled together before clustering, giving the clusterer a richer view of speaker characteristics from the cleaner separated audio
