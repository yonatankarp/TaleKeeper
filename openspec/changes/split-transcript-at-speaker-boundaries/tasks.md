## 1. Backend — Split function

- [x] 1.1 Implement `_split_transcript_segments(transcript_segs, speaker_segs) -> list[dict]` in `services/diarization.py`:
  - For each transcript segment, collect diarization speaker-change boundaries that fall strictly inside its `(start_time, end_time)` window
  - If no internal boundaries: yield segment unchanged
  - Otherwise: build sub-intervals at the boundaries, merge any sub-interval shorter than `MIN_SEGMENT_DURATION` into its neighbor, split `text` by word count proportional to sub-interval duration, return first sub-segment with original `id` and remaining with `id=None`

## 2. Backend — Wire into `run_final_diarization`

- [x] 2.1 Update both `SELECT` queries in `run_final_diarization` (one in the signed path, one in the unsigned path) to also fetch `session_id` and `text` from `transcript_segments` — needed for INSERTs of new sub-segments
- [x] 2.2 In the signed path of `run_final_diarization`, call `_split_transcript_segments(transcript_segs, segments)` before `align_speakers_with_transcript`
- [x] 2.3 In the unsigned path of `run_final_diarization`, call `_split_transcript_segments(transcript_segs, segments)` before `align_speakers_with_transcript`
- [x] 2.4 Update the DB write loop in both paths: when `seg["id"]` is `None`, INSERT a new `transcript_segments` row instead of UPDATE; otherwise UPDATE as before

## 3. Backend — Tests

- [x] 3.1 Unit test `_split_transcript_segments` — single-speaker overlap: segment unchanged
- [x] 3.2 Unit test `_split_transcript_segments` — two-speaker overlap: segment split into two sub-segments with correct `start_time`/`end_time`, proportional text, first sub keeps original `id`, second has `id=None`
- [x] 3.3 Unit test `_split_transcript_segments` — three-speaker overlap: segment splits into three sub-segments with correct proportions
- [x] 3.4 Unit test `_split_transcript_segments` — boundary shorter than `MIN_SEGMENT_DURATION` is merged with neighbor
- [x] 3.5 Unit test `_split_transcript_segments` — `[crosstalk]` diarization segment: transcript segment is split correctly and crosstalk sub-segment gets `is_overlap=1` after alignment (integration of split + align)
- [x] 3.6 Integration test: re-diarization on a session with long transcript segments produces more rows than before, each with correct speaker labels
