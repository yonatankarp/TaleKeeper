## Why

Speakers seated far from the microphone produce quiet audio segments. When WeSpeaker extracts embeddings from these low-amplitude segments, the resulting embeddings are poor quality — they don't capture the speaker's voice identity well. During spectral clustering, these weak embeddings get incorrectly merged with other speakers, degrading diarization accuracy. The diarization pipeline currently performs no amplitude normalization at any stage — raw audio segments are passed directly to the embedding model.

## What Changes

- Add **per-segment RMS normalization** before WeSpeaker embedding extraction. Each audio segment is scaled to a consistent target RMS level so that quiet and loud speakers produce equally strong input signals for the embedding model.
- Apply normalization in both embedding extraction paths: the main `_extract_embeddings_with_progress()` pipeline and the fine-stride `_extract_fine_stride_embeddings()` used by speaker change detection.

## Capabilities

### New Capabilities

_None — this is a pure implementation improvement within the existing diarization pipeline._

### Modified Capabilities

- `speaker-diarization`: Audio segments are now RMS-normalized before embedding extraction, improving embedding quality for quiet speakers.

## Impact

- **Backend**: `src/talekeeper/services/diarization.py` — new `_normalize_segment_audio()` helper, called in two existing functions before writing audio to temp WAV files.
- **Database**: No changes.
- **Frontend**: No changes.
- **Dependencies**: No new dependencies — uses only numpy operations already available.
- **Testing**: New unit test for the normalization helper. Existing tests unaffected (they mock embedding extraction).
