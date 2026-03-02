## Why

TaleKeeper currently has 1 test file with 10 tests covering only the speaker-merge endpoint. The remaining 10 routers (~2,000 lines), 8 services (~1,350 lines), the database layer, and the entire frontend are untested. Without meaningful test coverage, upgrading dependencies (FastAPI, speechbrain, faster-whisper, weasyprint, etc.) is risky — regressions can slip through silently. A comprehensive test suite is needed before any dependency upgrade cycle.

## What Changes

- Add pytest configuration with coverage reporting to `pyproject.toml`
- Add test dependencies (pytest, pytest-asyncio, pytest-cov, httpx) to a dev dependency group
- Add backend unit tests for all 8 service modules, mocking external dependencies (Whisper, speechbrain, Ollama/LLM, FFmpeg)
- Add backend integration tests for all 11 router modules using the existing httpx `AsyncClient` fixture pattern
- Add tests for the database layer (migrations, connection lifecycle, schema integrity)
- Add frontend test infrastructure (vitest + @testing-library/svelte) and unit tests for API client and key components
- Add a CI-friendly test runner script

## Capabilities

### New Capabilities
- `backend-test-infrastructure`: Pytest configuration, coverage thresholds, dev dependencies, shared fixtures and factories for campaigns/sessions/speakers/segments
- `router-tests`: Integration tests for all 11 API routers (campaigns, sessions, speakers, transcripts, summaries, exports, recording, images, roster, settings, voice-signatures)
- `service-tests`: Unit tests for all 8 services with mocked external dependencies (diarization, transcription, audio processing, summarization, image generation, LLM client, image client, setup)
- `database-tests`: Tests for schema migrations, connection management, and data integrity constraints
- `frontend-test-infrastructure`: Vitest configuration, Svelte testing-library setup, and unit tests for the API client and critical UI components

### Modified Capabilities
_(none — this change adds test coverage without altering any existing behavior or requirements)_

## Impact

- **Dependencies**: New dev-only dependencies — pytest-cov, factory-boy or similar fixtures, vitest, @testing-library/svelte, jsdom
- **Configuration**: New `[tool.pytest.ini_options]` section in pyproject.toml; new `vitest.config.ts` in frontend
- **CI**: Test suite should run in under 2 minutes without GPU/ML models loaded (all ML services mocked)
- **Code**: No production code changes — only new files under `tests/` and `frontend/src/**/*.test.ts`
- **Existing tests**: The existing `tests/test_merge_speakers.py` and `tests/conftest.py` remain as-is and continue to pass
