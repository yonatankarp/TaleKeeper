## Why

When multiple players speak simultaneously and at least one is far from the mic, their voices get merged into a single speaker cluster — their words are silently attributed to whoever was loudest. This corrupts session summaries by putting words in the wrong player's mouth, which is worse than a gap.

## What Changes

- After spectral clustering, detect subsegments whose embeddings sit ambiguously between two or more speaker clusters (post-clustering overlap detection using cosine distance ratio)
- Mark detected overlap segments as `[crosstalk]` in the transcript rather than assigning them to a single speaker
- Add an `is_overlap` flag to `transcript_segments` DB rows so the frontend can display and filter overlap segments distinctly
- Expose overlap segments in the transcript view with distinct visual treatment
- Exclude overlap time from per-speaker totals in the speaker panel

## Capabilities

### New Capabilities
- `overlap-detection`: Post-clustering detection of mixed-speaker segments using embedding ambiguity (ratio of cosine distance to nearest vs second-nearest cluster centroid). Flags segments as `[crosstalk]` rather than forcing single-speaker attribution.

### Modified Capabilities
- `speaker-diarization`: Diarization pipeline now produces overlap-flagged segments in addition to speaker-assigned segments. `align_speakers_with_transcript` must handle the `[crosstalk]` label.
- `transcription`: `transcript_segments` table gains an `is_overlap` boolean column. Migration required.

## Impact

- **Database**: New `is_overlap` column on `transcript_segments`. Migration required.
- **Backend**: `diarization.py` — new `_detect_overlap_segments()` called after clustering, before `_build_segments_from_labels()`. No new dependencies — purely geometric on already-computed embeddings and centroids.
- **Frontend**: Transcript tab renders `[crosstalk]` segments with muted styling. Speaker panel excludes overlap time from per-speaker totals.
- **No new ML models or dependencies.**
