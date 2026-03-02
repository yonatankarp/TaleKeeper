## Context

TaleKeeper is a FastAPI + Svelte application for recording and transcribing D&D sessions. It relies on heavy external dependencies (faster-whisper for transcription, speechbrain for speaker diarization, weasyprint for PDF export, Ollama for LLM/image generation). The project currently has a single test file (`tests/test_merge_speakers.py`) with 10 tests and a shared `conftest.py` providing database isolation and an httpx `AsyncClient` fixture. No frontend tests exist. The goal is to build a test suite comprehensive enough to catch regressions when upgrading any dependency.

## Goals / Non-Goals

**Goals:**
- Achieve meaningful coverage of all backend routers, services, and database operations
- Enable safe dependency upgrades by catching regressions in API contracts and service behavior
- Keep the test suite fast (< 2 min) by mocking all ML models and external services
- Add frontend test infrastructure and cover the API client layer and core component logic
- Preserve and build on the existing test patterns in `conftest.py`

**Non-Goals:**
- End-to-end browser tests (Playwright, Cypress) — too heavy for this phase
- Testing ML model accuracy (whisper transcription quality, diarization precision)
- Load/performance testing
- Achieving a specific coverage percentage target — focus on meaningful tests over metric chasing
- Testing third-party library internals (weasyprint rendering, FFmpeg codec behavior)

## Decisions

### 1. Backend test structure: mirror source layout under `tests/`

Tests follow the source structure: `tests/routers/test_campaigns.py` maps to `src/talekeeper/routers/campaigns.py`, `tests/services/test_diarization.py` maps to the corresponding service, etc. This makes it trivial to find the test for any module.

**Alternative considered**: Flat test directory. Rejected — doesn't scale with 20+ test files and makes discovery harder.

### 2. Fixture factories in `conftest.py` instead of factory-boy

Extend the existing `conftest.py` with simple async helper functions (`create_campaign()`, `create_session()`, `seed_speaker()`, etc.) that insert rows directly via `get_db()`. This avoids adding another dependency and matches the pattern already used in `test_merge_speakers.py`.

**Alternative considered**: factory-boy / factory-boy-asyncio. Rejected — adds a dependency for something achievable with ~50 lines of helper functions, and factory-boy's ORM integration doesn't align with the raw-SQL approach used here.

### 3. Mock strategy: patch at the service boundary

External dependencies are mocked at the service function level, not deep inside libraries. For example, `transcription.transcribe_audio()` gets mocked to return fake segments rather than mocking the WhisperModel internals. This tests the router-to-service integration while avoiding flaky ML dependencies.

Specific mock boundaries:
- **Whisper**: mock `faster_whisper.WhisperModel` — return canned segments
- **SpeechBrain**: mock `speechbrain.inference.EncoderClassifier` — return fake embeddings
- **LLM/Ollama**: mock `httpx.AsyncClient.post` in `llm_client.py` and `image_client.py` — return canned responses
- **FFmpeg/pydub**: mock `pydub.AudioSegment.from_file` — return a silent segment of known duration
- **WeasyPrint**: mock `weasyprint.HTML.write_pdf` — return dummy bytes

**Alternative considered**: Use real models with tiny test fixtures. Rejected — requires GPU/model downloads in CI, adds minutes to test runs, and tests model behavior rather than application logic.

### 4. Router tests: integration-level using httpx AsyncClient

Continue the pattern from `test_merge_speakers.py` — use the `client` fixture to hit actual FastAPI endpoints through httpx. This tests the full request/response cycle including validation, middleware, and error handling without a running server.

### 5. Database tests: schema verification and migration safety

Test that `init_db()` creates all expected tables with correct columns, that migrations are idempotent (running `init_db()` twice doesn't fail), and that foreign key constraints work as expected. No need for a migration framework test since the app uses inline schema DDL.

### 6. Frontend: vitest + @testing-library/svelte for component tests

Vitest is the natural choice for Vite-based projects — zero config for the build pipeline. `@testing-library/svelte` provides DOM testing for Svelte 5 components. Focus frontend tests on:
- `api.ts` — mock fetch, verify correct URLs/methods/error handling
- Key components with logic (e.g., `RecordingControls`, `SpeakerPanel`) — test state transitions and user interactions
- Skip pure-presentational components (`Spinner`, `AudioPlayer`)

**Alternative considered**: Playwright component testing. Rejected — heavier setup, slower, better suited for E2E which is a non-goal.

### 7. No CI pipeline in this change

The test suite will be runnable locally via `pytest` and `npm test`. CI integration (GitHub Actions, etc.) is a separate concern — this change focuses on the tests themselves.

## Risks / Trade-offs

- **Mock drift**: Mocked return values may diverge from real service responses over time → Mitigate by keeping mock data minimal and close to actual response shapes; document expected formats in fixture docstrings
- **Incomplete SSE/streaming coverage**: The recording and image endpoints use Server-Sent Events which are harder to test via httpx → Mitigate by testing the underlying service logic independently and testing SSE endpoints return the correct content-type and initial response
- **Svelte 5 testing maturity**: @testing-library/svelte support for Svelte 5 runes is relatively new → Mitigate by focusing frontend tests on the API layer and component logic rather than deep DOM assertions
- **Test maintenance burden**: 20+ new test files need ongoing maintenance → Mitigate by keeping tests focused on public API contracts rather than implementation details, so refactors don't break tests unnecessarily
