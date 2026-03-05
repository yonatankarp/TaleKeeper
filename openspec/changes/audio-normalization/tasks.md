## 1. Backend Implementation

- [ ] 1.1 Add `_normalize_segment_audio()` helper in `diarization.py` — takes `np.ndarray` and optional `target_rms` (default 0.1), returns normalized array; skips normalization if RMS < 1e-6; clips result to [-1.0, 1.0]
- [ ] 1.2 Apply `_normalize_segment_audio()` in `_extract_embeddings_with_progress()` — normalize `segment_audio` before `sf.write(tmp_path, segment_audio, sr)`
- [ ] 1.3 Apply `_normalize_segment_audio()` in `_extract_fine_stride_embeddings()` — normalize `segment_audio` before `sf.write(tmp_path, segment_audio, sr)`

## 2. Testing

- [ ] 2.1 Add unit test for `_normalize_segment_audio()` — verify output RMS matches target for a normal-amplitude input
- [ ] 2.2 Add unit test for `_normalize_segment_audio()` with near-silent input — verify RMS < 1e-6 passes through unchanged
- [ ] 2.3 Add unit test for `_normalize_segment_audio()` clipping — verify output is clipped to [-1.0, 1.0] when scaling would exceed range
- [ ] 2.4 Run full test suite (`make test`) and verify all tests pass

## 3. Validation

- [ ] 3.1 Manual test with real D&D session recording — compare speaker separation quality for quiet/distant speakers before and after normalization
