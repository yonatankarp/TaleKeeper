## Why

TaleKeeper's initial test suite (~53% coverage) established infrastructure and basic CRUD tests but left significant gaps in the most complex code paths: SSE streaming endpoints (recording, retranscription, re-diarization, image generation), file upload/download, roster sheet processing, and email sending. These are the riskiest code paths — they involve external I/O, streaming responses, and multi-step async workflows. Without tests for these paths, dependency upgrades and refactors remain risky.

## What Changes

- **Restructure test directories**: Reorganize from flat `tests/services/`, `tests/routers/`, `tests/db/` into two explicit layers — `tests/unit/` (service functions, all deps mocked) and `tests/integration/` (HTTP path, real DB, external I/O mocked).
- **Add SSE test helper**: A `parse_sse_events()` helper in `tests/conftest.py` for parsing Server-Sent Events from httpx responses.
- **Add integration tests for SSE endpoints**: process-audio, retranscribe, re-diarize, and generate-image — covering happy paths and error cases.
- **Add integration tests for file operations**: audio upload (MIME validation, replacement behavior), audio download (streaming, 404 cases).
- **Add integration tests for roster operations**: upload-sheet (PDF extraction via mocked fitz + LLM), import-url, refresh-sheet.
- **Add integration tests for exports**: printable PDF, POV-all ZIP, email send, email-not-configured.
- **Expand unit tests**: Diarization clustering with/without `num_speakers`, audio chunking edge cases.

## Capabilities

### New Capabilities

_(none — this change adds test coverage without altering any existing behavior)_

### Modified Capabilities

- `backend-test-infrastructure`: Test directory structure changes from flat to two-layer (unit/integration). New SSE parsing helper added to shared fixtures.

## Impact

- **Test structure**: `tests/services/*` moves to `tests/unit/services/`, `tests/db/*` to `tests/integration/db/`, `tests/routers/*` to `tests/integration/routers/`
- **No production code changes**: Only test files are added or moved
- **Coverage target**: ~53% → ~80%
- **No new dependencies**: Uses existing pytest, httpx, unittest.mock
