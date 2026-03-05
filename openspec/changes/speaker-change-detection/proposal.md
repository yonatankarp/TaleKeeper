## Why

D&D sessions have frequent rapid cross-talk where 3-6 players trade short phrases with minimal silence gaps. The current diarization pipeline (Silero VAD → WeSpeaker embeddings → spectral clustering) produces poor speaker separation in these scenes because VAD merges continuous cross-talk into single long segments, and the 1.2-second embedding windows within those segments capture mixed voices from multiple speakers. Clustering then receives contaminated embeddings and cannot cleanly separate speakers, causing them to be merged together. The clustering algorithm works correctly — the problem is the quality of its input.

## What Changes

- Add an **embedding-based speaker change detection** step between VAD and embedding extraction. For VAD segments longer than a configurable threshold (~2 seconds), extract embeddings at a fine stride (0.6s windows, 0.3s step), compute cosine distance between consecutive embeddings, and split at distance peaks that indicate speaker transitions.
- Replace the current single-pass embedding extraction with a two-phase approach: first detect speaker change points within long segments, then extract clean per-sub-segment embeddings for clustering.
- Make the change detection threshold and minimum segment duration configurable with sensible defaults tuned for D&D cross-talk.

## Capabilities

### New Capabilities

- `speaker-change-detection`: Detect speaker change points within long VAD segments using embedding cosine distance, producing finer-grained sub-segments that contain single-speaker speech for improved clustering accuracy.

### Modified Capabilities

- `speaker-diarization`: The diarization pipeline gains a speaker change detection stage between VAD and embedding extraction. Long VAD segments are sub-segmented at detected speaker boundaries before embeddings are extracted for clustering.

## Impact

- **Backend**: `src/talekeeper/services/diarization.py` — new `_detect_speaker_changes()` helper inserted between VAD and `_extract_embeddings_with_progress()`. The `diarize()` and `diarize_with_signatures()` functions gain an additional pipeline stage. SSE progress events extended to report change detection progress.
- **Database**: No schema changes.
- **Frontend**: No changes required. SSE progress events use existing event types with additional detail messages for the change detection phase.
- **Dependencies**: No new dependencies. Uses existing WeSpeaker ONNX model for fine-stride embedding extraction.
- **Testing**: New unit tests for `_detect_speaker_changes()`. Existing diarization tests updated to include the change detection stage in the mock pipeline.
