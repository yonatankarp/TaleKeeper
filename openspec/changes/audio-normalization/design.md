## Context

The diarization pipeline in `src/talekeeper/services/diarization.py` extracts WeSpeaker embeddings from audio segments by slicing the waveform, writing each slice to a temporary WAV file, and calling `model.extract_embedding(tmp_path)`. No amplitude normalization happens at any point — a segment from a speaker 2 meters from the mic might have 10-20x lower amplitude than one from a speaker sitting next to it. WeSpeaker's ResNet-based model is amplitude-sensitive: low-amplitude input produces noisier, less discriminative embeddings that cluster poorly.

Two functions extract embeddings:
- `_extract_embeddings_with_progress()` — main pipeline, 1.2s windows / 0.6s step
- `_extract_fine_stride_embeddings()` — speaker change detection, 0.6s windows / 0.3s step

Both follow the same pattern: slice audio → write temp WAV → extract embedding.

## Goals / Non-Goals

**Goals:**
- Normalize each audio segment to a consistent RMS level before WeSpeaker embedding extraction
- Improve embedding quality for quiet/distant speakers so they cluster correctly
- Keep the change minimal — single helper function, two call sites

**Non-Goals:**
- Global audio normalization (normalizing the entire file would not help per-segment variation)
- Dynamic range compression or noise reduction (different problems, different solutions)
- Making the target RMS configurable via UI (hardcode a sensible default)
- Changing how VAD, clustering, or segment building works

## Decisions

### 1. Per-segment RMS normalization with target level 0.1

Scale each audio segment so its RMS equals 0.1 (approximately -20 dBFS for float32 audio). Clip the result to [-1.0, 1.0] to prevent overflow.

**Why:** RMS normalization preserves the spectral characteristics (pitch, timbre) that WeSpeaker uses for speaker identity while equalizing loudness. A target of 0.1 is conservative — loud enough to produce strong embeddings, with headroom to avoid clipping. Peak normalization was rejected because it's sensitive to single spikes and doesn't represent overall loudness.

**Alternative considered:** Peak normalization (scale so max absolute value = 1.0). Rejected because a single loud click or pop would keep the entire segment quiet. RMS reflects average energy, which better represents the signal WeSpeaker sees.

**Alternative considered:** Loudness normalization (ITU-R BS.1770 / LUFS). Rejected as overkill — LUFS requires frequency weighting and gating, adding complexity for negligible benefit over simple RMS for short (0.6-1.2s) speech segments.

### 2. Skip normalization for near-silent segments

If a segment's RMS is below 1e-6 (effectively silence), skip normalization. Scaling near-zero audio would amplify noise to extreme levels.

**Why:** VAD occasionally lets through segments with minimal speech energy. Amplifying these would create garbage embeddings. Better to let them pass through at their natural (near-silent) level — the embedding will be weak but at least not dominated by amplified noise.

**Alternative considered:** Drop silent segments entirely. Rejected because the downstream pipeline already handles bad embeddings gracefully (they just don't contribute useful information to clustering).

### 3. Apply normalization at the segment-audio level, not the file level

Normalize each individual audio window (the numpy array) just before writing it to the temp WAV file, not at file load time.

**Why:** Different segments from the same file can have vastly different amplitudes (quiet speaker vs. loud speaker). File-level normalization would equalize the file's overall level but not the per-segment variation that causes the problem.

## Risks / Trade-offs

**[Clipping artifacts]** Aggressive normalization of a segment with a few loud peaks could clip after scaling. → Mitigated by `np.clip(-1.0, 1.0)` and the conservative target RMS of 0.1 which leaves headroom.

**[Noise amplification]** Very quiet segments may have their background noise amplified along with speech. → Mitigated by the silence threshold (RMS < 1e-6 skips normalization). For segments with low but nonzero speech, some noise amplification is acceptable — WeSpeaker is trained on varied recording conditions.

**[Embedding comparability]** Normalized and non-normalized embeddings exist in the same space but might have subtle distributional differences. → Not a concern because all segments in a single diarization run will be normalized consistently. Voice signatures generated from previous runs were already L2-normalized at the output level.
