## Context

The initial test suite (from the `full-test-coverage` change) established pytest infrastructure, shared fixtures, and basic tests for all routers and services. Coverage sits at ~53%. The remaining gaps are concentrated in:
- SSE streaming endpoints: recording (21%), transcripts (34%), speakers (67%)
- File I/O endpoints: audio upload/download, roster sheet processing, image file serving
- Complex integration paths: email sending, image generation with LLM scene crafting
- Service edge cases: diarization clustering modes, audio chunk boundary handling

The current test layout is flat (`tests/services/`, `tests/routers/`, `tests/db/`). All service tests mock external deps (unit-style), all router tests use real DB with httpx (integration-style), but this isn't explicit in the directory structure.

## Goals / Non-Goals

**Goals:**
- Restructure tests into explicit `unit/` and `integration/` layers
- Cover all SSE streaming endpoints (process-audio, retranscribe, re-diarize, generate-image)
- Cover file upload/download paths (audio, roster sheets, images)
- Cover email sending and export paths
- Reach ~80% overall backend coverage

**Non-Goals:**
- 100% line coverage (diminishing returns on generated code and error-only paths)
- Frontend test expansion (separate effort)
- Performance or load testing
- Testing with real ML models (all external deps remain mocked)

## Decisions

### 1. Two-layer test directory structure

**Decision**: Reorganize into `tests/unit/` (service functions, all deps mocked) and `tests/integration/` (HTTP → router → service → real DB, only external I/O mocked).

**Why**: Makes the testing philosophy explicit. Developers immediately know what's mocked vs. real by looking at the directory. The existing tests naturally fit — service tests are already unit-style, router tests are already integration-style.

**Alternative considered**: Keeping flat structure with naming conventions (`test_*_unit.py`, `test_*_integration.py`). Rejected because directories provide better organization and allow layer-specific conftest fixtures.

### 2. SSE test helper in shared conftest

**Decision**: Add `parse_sse_events(text: str) -> list[dict]` to `tests/conftest.py` that parses SSE-formatted text into `{event, data}` dicts with automatic JSON parsing of data fields.

**Why**: Multiple SSE endpoints need testing. A shared helper avoids duplication and provides consistent parsing. Placed in root conftest so both unit and integration tests can use it.

### 3. Mock boundaries for integration tests

**Decision**: Mock at the external boundary — the exact same boundaries as production code's external calls:

| Boundary | Patch target |
|---|---|
| Whisper STT | `talekeeper.services.transcription.get_model` |
| SpeechBrain ECAPA | `talekeeper.services.diarization.EncoderClassifier` |
| sklearn clustering | `talekeeper.services.diarization.AgglomerativeClustering` |
| pydub/ffmpeg | `pydub.AudioSegment.from_file` |
| WeasyPrint | `weasyprint.HTML` |
| PyMuPDF (fitz) | `fitz.open` |
| httpx | `httpx.AsyncClient.get` |
| OpenAI SDK | `talekeeper.services.image_client.AsyncOpenAI` |
| Ollama LLM | `talekeeper.services.llm_client.generate` |
| smtplib | `smtplib.SMTP` |
| Filesystem | Handled by `tmp_path` fixture |

**Why**: Black-box principle — tests verify behavior through public interfaces. If an underlying library is swapped (e.g., Whisper → another STT), the tests should still pass as long as the behavior is preserved. Mocking at the boundary achieves this.

### 4. Test organization within layers

**Decision**: Mirror the source structure within each layer:
- `tests/unit/services/test_<service>.py`
- `tests/integration/db/test_<topic>.py`
- `tests/integration/routers/test_<router>.py`

**Why**: Easy to find the test file for any source module. Standard pytest convention.

## Risks / Trade-offs

**[Test directory move may break IDE references]** → One-time fix. Running `pytest -v` after the move immediately validates that all tests are discovered.

**[SSE tests depend on response text format]** → The SSE format is defined by the HTTP spec and unlikely to change. The `parse_sse_events` helper abstracts the parsing.

**[Mock patch paths may differ from import paths]** → Some routers use lazy imports inside function bodies (e.g., `from weasyprint import HTML` inside the handler). Mocks must patch where the import lives, not where the module is defined. Each test documents the correct patch target.
