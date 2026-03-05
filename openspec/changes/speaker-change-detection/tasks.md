## 1. Core Change Detection

- [x] 1.1 Add module constants in `diarization.py`: `MIN_CHANGE_DETECTION_DURATION = 2.0`, `CHANGE_DETECTION_WINDOW = 0.6`, `CHANGE_DETECTION_STEP = 0.3`, `CHANGE_DETECTION_THRESHOLD = 0.4`, `CHANGE_DETECTION_MIN_SPLIT_GAP = 3`
- [x] 1.2 Implement `_extract_fine_stride_embeddings()` helper in `diarization.py` — for a single segment, extract WeSpeaker embeddings at 0.6s windows / 0.3s step, return `np.ndarray` of shape (N, 256) and list of window timestamps
- [x] 1.3 Implement `_find_speaker_change_points()` helper in `diarization.py` — given fine-stride embeddings, compute cosine distance between consecutive embeddings, use `scipy.signal.find_peaks()` with `height=CHANGE_DETECTION_THRESHOLD` and `distance=CHANGE_DETECTION_MIN_SPLIT_GAP`, return list of split timestamps
- [x] 1.4 Implement `_split_segment_at_changes()` helper in `diarization.py` — given a segment and split timestamps, produce sub-segments, merging any sub-segment shorter than `MIN_SEGMENT_DURATION` (0.4s) with its neighbor
- [x] 1.5 Implement `_detect_speaker_changes()` in `diarization.py` — iterate VAD segments, apply change detection to segments > `MIN_CHANGE_DETECTION_DURATION`, return refined segment list with short segments passed through unchanged; accept optional progress callback

## 2. Pipeline Integration

- [x] 2.1 Update `diarize()` to call `_detect_speaker_changes()` between `run_vad()` and `_extract_embeddings_with_progress()`, passing the progress callback
- [x] 2.2 Update `diarize_with_signatures()` to call `_detect_speaker_changes()` between `run_vad()` and `_extract_embeddings_with_progress()`, passing the progress callback
- [x] 2.3 Update `extract_speaker_embedding()` to call `_detect_speaker_changes()` between `run_vad()` and `_extract_embeddings_with_progress()`

## 3. SSE Progress Integration

- [x] 3.1 Add `change_detection_start` and `change_detection_done` stages to the progress callback in `diarize()` and `diarize_with_signatures()`
- [x] 3.2 Update `_diarization_progress()` in all four routers (`recording.py` process-audio, `recording.py` process-all, `speakers.py` re-diarize, `transcripts.py` retranscribe) to handle `change_detection_start` and `change_detection_done` events with appropriate SSE messages

## 4. Testing

- [x] 4.1 Add unit test for `_extract_fine_stride_embeddings()` — mock WeSpeaker, verify correct number of windows and embedding shape for a given segment duration
- [x] 4.2 Add unit test for `_find_speaker_change_points()` — pass embeddings with known speaker transitions (orthogonal vectors), verify change points are detected at the correct positions
- [x] 4.3 Add unit test for `_find_speaker_change_points()` with single-speaker embeddings — verify no change points detected when all embeddings are similar
- [x] 4.4 Add unit test for `_split_segment_at_changes()` — verify segment is correctly split at change points and sub-segments shorter than 0.4s are merged
- [x] 4.5 Add unit test for `_detect_speaker_changes()` — verify short segments pass through unchanged and long segments are processed
- [x] 4.6 Update `test_diarize` to verify `_detect_speaker_changes()` is called in the pipeline
- [x] 4.7 Run full test suite (`make test`) and verify all tests pass

## 5. Validation

- [x] 5.1 Manual test with real D&D session recording — compare speaker separation quality before and after change detection, specifically in cross-talk sections
