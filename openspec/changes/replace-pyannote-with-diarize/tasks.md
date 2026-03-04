## 1. Dependencies

- [ ] 1.1 Remove `pyannote.audio>=3.3` from `pyproject.toml` and add `diarize>=0.1.0,<0.2.0`
- [ ] 1.2 Run `venv/bin/pip install -e ".[dev]"` and verify diarize imports work

## 2. Database

- [ ] 2.1 Update default `similarity_threshold` from 0.65 to 0.75 in campaigns table schema (`src/talekeeper/db/connection.py`)

## 3. Core Diarization Service

- [ ] 3.1 Implement `_extract_embeddings_with_progress()` helper in `diarization.py` — iterate speech segments, window into 1.2s chunks with 0.6s step, call `wespeakerruntime.Speaker` per chunk, invoke progress callback with (current, total) after each segment
- [ ] 3.2 Implement `_build_segments_from_labels()` helper — convert diarize clustering output (speech segments, subsegments, labels) into `list[SpeakerSegment]`, merge adjacent same-speaker segments
- [ ] 3.3 Rewrite `diarize()` function — call `run_vad()` → `_extract_embeddings_with_progress()` → `cluster_speakers()` → `_build_segments_from_labels()`, accept optional progress callback, return `list[SpeakerSegment]`
- [ ] 3.4 Rewrite `diarize_with_signatures()` — run full pipeline, group embeddings by speaker label via time overlap, compute L2-normalized centroids, match against stored signatures with cosine similarity, return `list[SpeakerSegment]`
- [ ] 3.5 Rewrite `extract_speaker_embedding()` — run VAD, extract embeddings, filter subsegments overlapping with provided time ranges, average + L2-normalize, return 256-dim `np.ndarray`
- [ ] 3.6 Delete `_get_pipeline()`, `_get_embedding_model()`, `_patch_torchaudio_compat()`, `_diarization_hook()`, and global `_pipeline`/`_embedding_model` caches
- [ ] 3.7 Simplify `unload_models()` to just `gc.collect()` (no pipeline/embedding model to unload)
- [ ] 3.8 Keep `_resolve_hf_token()` unchanged (unused by diarize but kept for future flexibility)

## 4. Resource Orchestration

- [ ] 4.1 Simplify `cleanup_diarization()` in `resource_orchestration.py` — remove `diarization.unload_models()` call, keep `gc.collect()`

## 5. SSE Progress Integration

- [ ] 5.1 Update `run_final_diarization()` to accept an optional progress callback and pass it through to `diarize()` and `diarize_with_signatures()`
- [ ] 5.2 Update `process-audio` SSE endpoint in `recording.py` to pass a progress callback that emits SSE events for each diarization stage (VAD, embeddings X/Y, clustering)
- [ ] 5.3 Update `process-all` SSE endpoint in `recording.py` to pass the same progress callback for diarization phase
- [ ] 5.4 Update `re-diarize` SSE endpoint in `speakers.py` to pass the same progress callback for diarization phase
- [ ] 5.5 Update `retranscribe` SSE endpoint in `transcripts.py` to pass the same progress callback for diarization phase

## 6. Testing

- [ ] 6.1 Rewrite `test_diarize_with_pyannote` to mock `diarize.vad.run_vad`, `wespeakerruntime.Speaker`, and `diarize.clustering.cluster_speakers` instead of pyannote imports
- [ ] 6.2 Rewrite `test_diarize_passes_num_speakers` to verify `num_speakers` is passed to `cluster_speakers()`
- [ ] 6.3 Rewrite `test_diarize_with_signatures_matches_above_threshold` with mocked 256-dim WeSpeaker embeddings and cosine similarity matching
- [ ] 6.4 Rewrite `test_diarize_with_signatures_unknown_below_threshold` with mocked 256-dim embeddings
- [ ] 6.5 Update `test_resolve_hf_token_from_settings` and `test_resolve_hf_token_from_env` — keep unchanged (function is preserved)
- [ ] 6.6 Add test for `_extract_embeddings_with_progress` — verify progress callback is invoked with correct (current, total) values
- [ ] 6.7 Add test for `_build_segments_from_labels` — verify correct `SpeakerSegment` output from diarize clustering labels
- [ ] 6.8 Verify existing integration tests pass without changes (they mock at service level)

## 7. Validation

- [ ] 7.1 Run full test suite (`make test`) and verify all tests pass
- [ ] 7.2 Manual test with real 2h D&D session recording — verify diarization completes, speakers are correctly separated, and SSE progress events are emitted
