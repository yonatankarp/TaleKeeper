## 1. Backend Test Infrastructure

- [x] 1.1 Add `[project.optional-dependencies]` dev group to `pyproject.toml` with pytest, pytest-asyncio, pytest-cov, httpx
- [x] 1.2 Add `[tool.pytest.ini_options]` section to `pyproject.toml` (asyncio_mode = "auto", testpaths = ["tests"])
- [x] 1.3 Add `db` fixture to `tests/conftest.py` that yields an initialized aiosqlite connection to a temp database
- [x] 1.4 Add `create_campaign()` async helper to `tests/conftest.py`
- [x] 1.5 Add `create_session()` async helper to `tests/conftest.py`
- [x] 1.6 Add `create_speaker()` async helper to `tests/conftest.py`
- [x] 1.7 Add `create_segment()` async helper to `tests/conftest.py`
- [x] 1.8 Verify `pip install -e ".[dev]"` installs all test deps and `pytest` runs successfully

## 2. Database Tests

- [x] 2.1 Create `tests/db/test_schema.py` — test all 9 tables exist after `init_db()` and columns match expected DDL
- [x] 2.2 Add migration idempotency tests — double `init_db()` and individual migration functions on already-migrated DB
- [x] 2.3 Add foreign key cascade tests — campaign→sessions, session→speakers+segments, speaker deletion sets segment speaker_id to NULL
- [x] 2.4 Add `get_db()` lifecycle tests — connection is usable and properly closed after context exit
- [x] 2.5 Add default value tests — campaign defaults (language, num_speakers, description) and session defaults (status, language)

## 3. Router Tests — CRUD Routers

- [x] 3.1 Create `tests/routers/test_campaigns.py` — create, list, get, update, delete, dashboard (6 tests)
- [x] 3.2 Create `tests/routers/test_sessions.py` — create, list, get, update, delete (5 tests)
- [x] 3.3 Create `tests/routers/test_roster.py` — create, list, update, delete (4 tests)
- [x] 3.4 Create `tests/routers/test_settings.py` — get empty, update+retrieve, password masking (3 tests)
- [x] 3.5 Create `tests/routers/test_transcripts.py` — get with segments, get empty session (2 tests)

## 4. Router Tests — Speakers & Voice Signatures

- [x] 4.1 Create `tests/routers/test_speakers.py` — list, update, reassign segment, bulk reassign, speaker suggestions (5 tests)
- [x] 4.2 Create `tests/routers/test_voice_signatures.py` — list, delete (2 tests)

## 5. Router Tests — Summaries, Exports, Images, Recording

- [x] 5.1 Create `tests/routers/test_summaries.py` — list, generate full (mocked LLM), update, delete, LLM status (5 tests)
- [x] 5.2 Create `tests/routers/test_exports.py` — PDF (mocked WeasyPrint), text, transcript, email content (4 tests)
- [x] 5.3 Create `tests/routers/test_images.py` — list, delete, image health (mocked), craft scene (mocked LLM) (4 tests)
- [x] 5.4 Create `tests/routers/test_recording.py` — upload audio file (1 test)

## 6. Router Tests — Error Handling

- [x] 6.1 Add 404 tests across router test files — nonexistent campaign, session, roster entry (add to existing test files from tasks 3-5)

## 7. Service Tests — Audio & Transcription

- [x] 7.1 Create `tests/services/test_audio.py` — audio_to_wav, webm_to_wav (mocked pydub), split_audio_to_chunks, compute_primary_zone (4 tests)
- [x] 7.2 Create `tests/services/test_transcription.py` — transcribe, transcribe_stream, transcribe_chunked (mocked WhisperModel), model caching (4 tests)

## 8. Service Tests — Diarization

- [x] 8.1 Create `tests/services/test_diarization.py` — diarize (mocked encoder), diarize_with_signatures, align_speakers_with_transcript, merge_segments (4 tests)

## 9. Service Tests — LLM, Image, Summarization

- [x] 9.1 Create `tests/services/test_llm_client.py` — health_check success, health_check failure, generate, resolve_config (4 tests)
- [x] 9.2 Create `tests/services/test_image_client.py` — health_check, generate_image (2 tests)
- [x] 9.3 Create `tests/services/test_image_generation.py` — craft_scene_description, generate_session_image stores in DB (2 tests)
- [x] 9.4 Create `tests/services/test_summarization.py` — generate_full_summary, generate_pov_summary (mocked LLM), format_transcript, chunk_transcript (4 tests)
- [x] 9.5 Create `tests/services/test_setup.py` — check_first_run on fresh data dir (1 test)

## 10. Frontend Test Infrastructure

- [x] 10.1 Add vitest, @testing-library/svelte, @testing-library/jest-dom, jsdom to `frontend/package.json` devDependencies
- [x] 10.2 Create `frontend/vitest.config.ts` with Svelte plugin, jsdom environment, and `$lib` alias
- [x] 10.3 Add `"test": "vitest run"` script to `frontend/package.json`

## 11. Frontend API Client Tests

- [x] 11.1 Create `frontend/src/lib/api.test.ts` — api.get, api.post, api.put, api.del with mocked fetch (4 tests)
- [x] 11.2 Add API error handling test — non-ok response throws with error message (1 test)
- [x] 11.3 Add mergeSpeakers test — correct URL and payload (1 test)
- [x] 11.4 Add uploadAudio test — multipart FormData sent (1 test)

## 12. Frontend SSE Streaming Tests

- [x] 12.1 Add generateImageStream test — onPhase and onDone callbacks invoked correctly (1 test)
- [x] 12.2 Add reDiarize test — onError callback invoked on error event (1 test)
- [x] 12.3 Add processAudio test — onProgress callback invoked with chunk/total (1 test)

## 13. Verification

- [x] 13.1 Run full backend test suite with `pytest -v` — all tests pass
- [x] 13.2 Run `pytest --cov=talekeeper` — coverage report generated for all modules
- [x] 13.3 Run `npm test` in frontend/ — all frontend tests pass
- [x] 13.4 Verify existing `test_merge_speakers.py` still passes unchanged
