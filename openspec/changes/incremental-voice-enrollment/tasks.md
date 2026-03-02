## 1. Backend Service — enroll_speaker_voice

- [ ] 1.1 Add `enroll_speaker_voice` async function to `src/talekeeper/services/diarization.py` — queries speaker/session/roster info, samples up to 120s of segments (longest first), extracts embedding via `extract_speaker_embedding`, creates new or weighted-merges existing voice signature
- [ ] 1.2 Add unit test for new signature creation path (`tests/unit/services/test_enroll_voice.py`) — mock audio pipeline, verify signature row created with correct embedding and num_samples
- [ ] 1.3 Add unit test for weighted merge with existing signature — verify num_samples accumulates and merged embedding direction is weighted toward the larger sample count
- [ ] 1.4 Add unit test for 120s audio sampling cap — create segments totalling 300s, verify `extract_speaker_embedding` receives time_ranges capped at ~120s
- [ ] 1.5 Add unit tests for no-op edge cases — no roster match, no audio path, no segments: verify no signature created and no errors raised

## 2. Backend Router — Wire enrollment trigger

- [ ] 2.1 Modify `PUT /api/speakers/{id}` in `src/talekeeper/routers/speakers.py` to accept `BackgroundTasks`, check if updated player_name + character_name match an active roster entry, and schedule `enroll_speaker_voice` as a background task
- [ ] 2.2 Add integration test verifying enrollment is triggered when speaker is assigned to a matching roster entry (`tests/integration/routers/test_speakers.py`)
- [ ] 2.3 Add integration test verifying enrollment is NOT triggered when names don't match any roster entry

## 3. Verification

- [ ] 3.1 Run full test suite (`.venv/bin/python -m pytest -v`) — verify no regressions across all existing tests
