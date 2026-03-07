## 1. Database

- [ ] 1.1 Add `is_overlap INTEGER NOT NULL DEFAULT 0` column to `transcript_segments` via additive migration in `db/connection.py`
- [ ] 1.2 Verify migration leaves all existing rows with `is_overlap = 0` and unmodified `speaker_id` values

## 2. Backend — Overlap Detection

- [ ] 2.1 Add `OVERLAP_RATIO_THRESHOLD = 0.85` constant to `services/diarization.py` alongside existing constants
- [ ] 2.2 Implement `_flag_overlap_subsegments(embeddings, labels, threshold) -> np.ndarray` returning a boolean mask — computes per-cluster centroids from `(embeddings, labels)`, then flags each embedding where `sim_to_second / sim_to_best >= threshold`
- [ ] 2.3 Wire `_flag_overlap_subsegments` into `diarize()`: call after `cluster_speakers`, pass boolean mask to `_build_segments_from_labels`
- [ ] 2.4 Wire `_flag_overlap_subsegments` into `diarize_with_signatures()`: call after `cluster_speakers`, use boolean mask to assign `[crosstalk]` label before building output segments (skip signature matching for flagged subsegments)
- [ ] 2.5 Update `_build_segments_from_labels` to accept an optional `overlap_mask` parameter and assign `[crosstalk]` label to masked subsegments
- [ ] 2.6 Update `align_speakers_with_transcript` to pass `[crosstalk]`-labelled segments through without attempting speaker lookup — set `is_overlap = 1`, `speaker_id = None` on matched transcript segments
- [ ] 2.7 Update `run_final_diarization` to write `is_overlap = 1` when inserting/updating `transcript_segments` rows that align to `[crosstalk]` segments

## 3. Backend — API

- [ ] 3.1 Update transcript segment response schema (Pydantic model in `routers/transcripts.py`) to include `is_overlap: bool`
- [ ] 3.2 Verify the `/sessions/{id}/transcript` endpoint returns `is_overlap` for each segment
- [ ] 3.3 Update speaker panel endpoint (`routers/speakers.py`) to exclude `is_overlap = 1` segments from per-speaker speaking time totals

## 4. Backend — Tests

- [ ] 4.1 Unit test `_flag_overlap_subsegments`: ambiguous embedding (ratio >= 0.85) flagged, clear embedding not flagged, single-cluster input produces empty mask
- [ ] 4.2 Unit test `_build_segments_from_labels` with overlap mask: masked subsegments get `[crosstalk]` label
- [ ] 4.3 Unit test `align_speakers_with_transcript`: segment overlapping a `[crosstalk]` diarization segment gets `is_overlap = True`, `speaker_label = None`
- [ ] 4.4 Integration test: DB migration produces `is_overlap = 0` for all pre-existing rows
- [ ] 4.5 Integration test: transcript endpoint returns `is_overlap` field on each segment

## 5. Frontend

- [ ] 5.1 Update transcript segment TypeScript type in `lib/api.ts` (or equivalent) to include `is_overlap: boolean`
- [ ] 5.2 In the transcript tab component, render segments where `is_overlap === true` with muted styling and the label `"[crosstalk]"` instead of a speaker name
- [ ] 5.3 Exclude `[crosstalk]` segments from the speaker name filter (searching by speaker name must not surface overlap segments)
- [ ] 5.4 In the speaker panel component, exclude overlap segments from per-speaker speaking time totals
