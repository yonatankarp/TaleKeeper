## 1. Database

- [ ] 1.1 Add `source_separation_enabled INTEGER NOT NULL DEFAULT 0` column to `campaigns` table via additive migration in `db/connection.py`
- [ ] 1.2 Verify migration leaves all existing campaign rows with `source_separation_enabled = 0`

## 2. Separation Service

- [ ] 2.1 Add `speechbrain` to dependencies in `pyproject.toml`
- [ ] 2.2 Create `src/talekeeper/services/separation.py` with `separate_audio(wav_path: Path, progress_callback: ProgressCallback | None) -> list[Path]` — runs SepFormer on the full audio chunked into 30-second windows, writes 2 separated stream temp WAV files, returns their paths
- [ ] 2.3 Implement model download and caching in `separate_audio` — use SpeechBrain's pretrained `speechbrain/sepformer-wsj02mix`, cache to `~/.cache/speechbrain/`
- [ ] 2.4 Emit `separation_downloading` progress event during first-run model download, `separation_start` before inference, `separation_done` after streams are written
- [ ] 2.5 Wrap `separate_audio` to catch all exceptions: log the error, emit `separation_error` progress event with the error message, return empty list to signal fallback to original audio

## 3. Diarization Pipeline Integration

- [ ] 3.1 Update `diarize()` in `services/diarization.py` to accept an optional `source_separation_enabled: bool = False` parameter
- [ ] 3.2 In `diarize()`, when `source_separation_enabled=True`: call `separate_audio()`, run VAD and embedding extraction on each returned stream, pool all embeddings before clustering; fall back to original audio if `separate_audio` returns empty list
- [ ] 3.3 Update `diarize_with_signatures()` with the same `source_separation_enabled` parameter and identical integration
- [ ] 3.4 Ensure separated stream temp files are deleted in `finally` blocks in both `diarize()` and `diarize_with_signatures()`
- [ ] 3.5 Update `run_final_diarization()` to fetch `source_separation_enabled` from the campaign row and pass it through to `diarize()` / `diarize_with_signatures()`

## 4. Re-diarization Integration

- [ ] 4.1 Update `routers/transcripts.py` re-diarize endpoint to fetch `source_separation_enabled` from the session's campaign and pass it to `run_final_diarization()`
- [ ] 4.2 Verify `separation_start`, `separation_done`, and `separation_error` SSE progress events are forwarded through the re-diarize SSE stream

## 5. Backend — Campaign API

- [ ] 5.1 Update campaign Pydantic request/response models in `routers/campaigns.py` to include `source_separation_enabled: bool`
- [ ] 5.2 Update campaign `GET` and `PUT` endpoints to read and write `source_separation_enabled`

## 6. Backend — Tests

- [ ] 6.1 Unit test `separate_audio`: mock SpeechBrain, verify 2 temp files are created, verify they are cleaned up on both success and exception
- [ ] 6.2 Unit test `diarize()` with `source_separation_enabled=True`: verify `separate_audio` is called and its streams are passed to VAD+embedding
- [ ] 6.3 Unit test `diarize()` with `source_separation_enabled=True` and separation failure: verify fallback to original audio occurs
- [ ] 6.4 Integration test: campaign `PUT` saves and returns `source_separation_enabled`
- [ ] 6.5 Integration test: DB migration sets `source_separation_enabled = 0` on existing campaigns

## 7. Frontend

- [ ] 7.1 Add `source_separation_enabled` to the campaign TypeScript type in `lib/api.ts`
- [ ] 7.2 Add a toggle in the campaign creation and edit forms labelled "Enable source separation" with a warning note about processing time
- [ ] 7.3 Wire the toggle to the campaign `PUT` request body
- [ ] 7.4 Display `separation_start` and `separation_done` progress events in the diarization progress UI (same treatment as existing VAD/embedding stage events)
- [ ] 7.5 Display `separation_error` as a dismissible warning in the progress UI (not a fatal error — diarization continues)
