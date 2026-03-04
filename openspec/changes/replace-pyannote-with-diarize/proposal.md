## Why

Pyannote's MPS backend produces incorrect timestamps and wrong speaker assignments on Apple Silicon (confirmed by maintainer, issue #1337, wontfix). Running on CPU instead takes 2-3 hours for a 2-hour D&D session, and the speaker merging problem (multiple distinct speakers collapsed into one) persists. The `diarize` library (FoxNoseTech, Apache 2.0) provides a 7x faster CPU-only pipeline using Silero VAD + WeSpeaker ONNX embeddings + spectral clustering, with competitive accuracy for 1-7 speakers and no HuggingFace token requirement.

## What Changes

- **BREAKING**: Replace pyannote.audio with `diarize` library as the diarization backend. Voice signature embeddings change from 192-dim (pyannote) to 256-dim (WeSpeaker). Existing voice signatures must be regenerated.
- Replace agglomerative clustering with spectral clustering for speaker assignment.
- Replace pyannote's segmentation model with Silero VAD for speech activity detection.
- Replace pyannote's ECAPA-TDNN embeddings with WeSpeaker ResNet34-LM ONNX embeddings (256-dim).
- Remove MPS device targeting (diarize is CPU-only, no GPU bugs).
- Remove HuggingFace token requirement for diarization (models auto-download, no gating).
- Add per-stage SSE progress reporting (VAD, embeddings with X/Y counter, clustering) instead of pyannote's internal hook.
- Update default similarity threshold from 0.65 to 0.75 for new campaigns (WeSpeaker embedding distribution).
- Remove pyannote.audio dependency from pyproject.toml, add diarize>=0.1.0.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `speaker-diarization`: Replace pyannote pipeline with diarize library. Agglomerative clustering becomes spectral clustering. `num_speakers` becomes a direct clustering input (not a post-hoc constraint). Remove real-time chunk diarization references to pyannote-specific parameters. Add per-stage progress reporting.
- `voice-signatures`: Replace ECAPA-TDNN encoder with WeSpeaker ResNet34-LM for embedding extraction (192-dim to 256-dim). Remove HuggingFace token requirement for embedding extraction. Update similarity threshold default to 0.75.
- `session-re-diarization`: Update SSE progress events to report per-stage progress (VAD segments found, embedding extraction X/Y, clustering result).

## Impact

- **Backend**: `diarization.py` fully rewritten (same public API). `resource_orchestration.py` simplified (no models to unload). `pyproject.toml` dependency swap.
- **Database**: Default `similarity_threshold` updated to 0.75 for new campaigns. Existing voice signatures incompatible (dimension change) and must be regenerated.
- **Frontend**: No changes required. SSE progress events use same event types with updated detail messages.
- **Dependencies**: Remove `pyannote.audio>=3.3`. Add `diarize>=0.1.0` (brings `wespeakerruntime`, `silero-vad`, `scikit-learn`; `torch` already present).
- **Testing**: Unit test mocks change from pyannote to diarize imports. Integration tests unchanged.
