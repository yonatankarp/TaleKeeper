## Context

The diarization pipeline in `src/talekeeper/services/diarization.py` currently runs: Silero VAD → WeSpeaker embedding extraction (1.2s windows, 0.6s step) → spectral clustering. VAD outputs speech segments representing continuous speech regions. Long segments (e.g., 15-30 seconds of cross-talk) are windowed for embedding extraction, but each 1.2s window may capture mixed voices from multiple speakers. Spectral clustering then receives these contaminated embeddings and cannot cleanly separate speakers, causing them to be merged.

The existing `_extract_embeddings_with_progress()` function already loads audio via `soundfile`, initializes a `wespeakerruntime.Speaker` model, and extracts embeddings per window. The WeSpeaker model produces 256-dim embeddings from WAV files via temp file I/O.

SSE progress reporting follows the pattern: the diarization functions accept an optional `ProgressCallback` and emit stage-keyed events (`vad_start`, `vad_done`, `embeddings`, `clustering_start`, `clustering_done`). Routers collect events in a list and yield them after `run_final_diarization()` returns.

## Goals / Non-Goals

**Goals:**
- Improve speaker separation accuracy in rapid cross-talk by splitting long VAD segments at speaker change points before embedding extraction
- Keep the change contained to `diarization.py` — no router, database, or frontend changes
- Maintain the existing progress callback pattern and extend it with change detection progress events
- Preserve identical public API surface (`diarize()`, `diarize_with_signatures()`, `extract_speaker_embedding()`, `run_final_diarization()`)

**Non-Goals:**
- Handling true overlapping speech (two people speaking simultaneously) — this requires fundamentally different models (e.g., end-to-end neural diarization)
- Replacing spectral clustering or the WeSpeaker embedding model
- Making change detection parameters user-configurable via the UI (hardcode sensible defaults, add settings later if needed)
- Improving chunk diarization during recording (this only affects the final diarization pass)

## Decisions

### 1. Insert change detection between VAD and embedding extraction

Add a `_detect_speaker_changes()` function that takes VAD segments and returns finer-grained sub-segments. It runs only on segments longer than `MIN_CHANGE_DETECTION_DURATION` (2.0 seconds). Short segments pass through unchanged.

**Why:** This is the minimal insertion point — it refines VAD output without changing the downstream embedding extraction or clustering logic. The existing `_extract_embeddings_with_progress()` already accepts a list of segments, so it receives the refined segments transparently.

**Alternative considered:** Modify `_extract_embeddings_with_progress()` to detect changes internally while extracting embeddings. Rejected because it conflates two concerns (change detection and embedding extraction) and makes the change detection logic harder to test independently.

### 2. Use embedding cosine distance for change detection

For each long segment, extract embeddings at a fine stride (0.6s windows, 0.3s step), compute cosine distance between consecutive embeddings, and split at peaks where distance exceeds a threshold.

**Why:** WeSpeaker embeddings already encode speaker identity. When the speaker changes, consecutive embeddings will have high cosine distance. This reuses the model we already load and directly measures what we care about — voice identity change.

**Alternative considered:** BIC (Bayesian Information Criterion) segmentation using MFCC features. More compute-efficient but less accurate for speaker-specific changes (BIC detects acoustic changes generally, not speaker changes specifically). Also would require computing MFCCs separately from the WeSpeaker pipeline.

**Alternative considered:** Energy-based splitting (split at volume dips). Rejected because D&D cross-talk has continuous energy with no reliable dips between speakers.

### 3. Peak detection with minimum distance and prominence

Use scipy's `find_peaks()` on the cosine distance signal with parameters: `distance` (minimum samples between peaks, prevents over-splitting) and `height` (minimum cosine distance for a split). Default `height=0.4`, `distance=3` (i.e., ~0.9 seconds between splits given 0.3s step).

**Why:** Simple peak detection with tunable parameters. The `height` threshold controls sensitivity — higher means fewer splits (only obvious speaker changes), lower means more aggressive splitting. The `distance` parameter prevents splitting into sub-second fragments that are too short for meaningful embeddings.

**Alternative considered:** Fixed threshold with no peak detection (split whenever distance > threshold for any consecutive pair). Rejected because it creates many spurious split points in noisy distance signals. Peak detection naturally finds the most prominent transitions.

### 4. Reuse the same WeSpeaker model instance

The change detection step initializes `wespeakerruntime.Speaker(lang="en")` — the same model used later by `_extract_embeddings_with_progress()`. Each call initializes its own instance since we don't cache models globally (design decision #6 from the diarize migration).

**Why:** The ONNX model loads in <1s. Sharing an instance between change detection and embedding extraction would require threading a model parameter through the API, adding complexity for negligible performance gain.

**Alternative considered:** Cache the model instance and share between the two stages. Rejected as premature optimization — the model load time is negligible compared to the actual embedding extraction time for hundreds of segments.

### 5. Change detection segments replace original VAD segments in the pipeline

After change detection, the original long VAD segment is replaced in the segments list by its sub-segments. These sub-segments have the same structure (start, end) as VAD segments, so downstream code needs no changes.

**Why:** The pipeline is already segment-agnostic — `_extract_embeddings_with_progress()` iterates over segments regardless of their source. Replacing segments in-place means no changes to embedding extraction, clustering, or segment building.

**Alternative considered:** Keep both original and sub-segments, using a nested structure. Rejected because it would require changes throughout the pipeline to handle the nesting.

### 6. Default parameters tuned for D&D cross-talk

- `MIN_CHANGE_DETECTION_DURATION = 2.0` — only process segments longer than 2 seconds (short segments are likely single-speaker)
- `CHANGE_DETECTION_WINDOW = 0.6` — window size for fine-stride embedding extraction
- `CHANGE_DETECTION_STEP = 0.3` — step size (50% overlap)
- `CHANGE_DETECTION_THRESHOLD = 0.4` — minimum cosine distance to consider a speaker change
- `CHANGE_DETECTION_MIN_SPLIT_GAP = 3` — minimum peak distance in steps (~0.9 seconds between splits)

**Why:** D&D has rapid turn-taking but speakers usually hold the floor for at least 1 second. A 0.4 cosine distance threshold is moderate — high enough to ignore within-speaker variation, low enough to catch different speakers. These can be tuned empirically.

**Alternative considered:** Make all parameters configurable via campaign settings. Rejected for now — adding 5 new settings to the UI is premature. Start with hardcoded defaults, expose settings later if users need tuning.

## Risks / Trade-offs

**[Increased processing time]** Change detection adds a fine-stride embedding extraction pass over long segments before the main extraction. For a 2-hour session with many long cross-talk segments, this could add 20-40% to total diarization time. → Acceptable trade-off for meaningfully better speaker separation. The change detection pass is smaller (only long segments, not all segments) and uses the same fast ONNX model.

**[Over-splitting]** Aggressive change detection could split mid-sentence pauses or pitch changes within a single speaker into separate segments. → Mitigated by the `height` threshold (0.4) and `distance` parameter (3 steps minimum). Under-splitting (missing a change) is worse than over-splitting (splitting within a speaker) because clustering can merge same-speaker sub-segments, but cannot separate mixed-speaker segments.

**[Threshold sensitivity]** The cosine distance threshold (0.4) may need tuning for different recording conditions (room acoustics, microphone type, speaker similarity). → Start with 0.4, evaluate on real sessions. The threshold is a module constant, easy to adjust. Could be made configurable later if needed.

**[scipy dependency for peak detection]** `find_peaks()` requires scipy, which is already in the dependency tree (`scikit-learn` depends on it). No new dependency needed.

## Open Questions

- Is 0.4 the right cosine distance threshold for D&D recordings with 6 speakers? May need empirical tuning after the first real-session test.
- Should very long segments (>30s) be handled differently, e.g., with a coarser initial pass before fine-stride detection? Unlikely to matter for D&D but worth monitoring.
