# Black-Box Test Coverage Improvement

**Date:** 2026-03-02
**Goal:** Increase backend test coverage from ~53% to ~80% using a two-layer testing strategy that is library-agnostic.

## Principles

- **Black box:** Tests verify behavior through public interfaces, not implementation details.
- **Library-agnostic:** If you swap Whisper for another STT, or pydub for ffmpeg-python, the tests still pass.
- **Two layers:** Unit tests for service logic, integration tests for the full HTTP path.
- **Real DB:** Integration tests use a real temp SQLite database. Only external I/O is mocked.

## Directory Structure

```
tests/
  conftest.py                  # shared: db, client, factory helpers
  test_merge_speakers.py       # existing, stays in place

  unit/                        # Layer 1: function-level, all deps mocked
    services/
      test_audio.py
      test_transcription.py
      test_diarization.py
      test_llm_client.py
      test_image_client.py
      test_image_generation.py
      test_summarization.py
      test_setup.py

  integration/                 # Layer 2: HTTP -> router -> service -> real DB
    conftest.py                # integration-specific mock fixtures
    db/
      test_schema.py
    routers/
      test_campaigns.py
      test_sessions.py
      test_roster.py
      test_settings.py
      test_transcripts.py
      test_speakers.py
      test_summaries.py
      test_exports.py
      test_images.py
      test_recording.py
      test_voice_signatures.py
```

Existing tests move from `tests/db/`, `tests/routers/`, `tests/services/` into the appropriate layer. The existing service tests are unit-style (mocked deps) so they go to `unit/`. The existing router/db tests are integration-style (real DB via `client` fixture) so they go to `integration/`.

## Mock Boundaries (Integration Layer)

These external boundaries are mocked. Everything else (routers, services, DB) runs for real.

| Boundary | What it replaces | Patch target |
|---|---|---|
| Whisper STT | Speech-to-text model | `talekeeper.services.transcription.get_model` |
| SpeechBrain ECAPA | Speaker embeddings | `talekeeper.services.diarization.EncoderClassifier` |
| sklearn clustering | Speaker clustering | `talekeeper.services.diarization.AgglomerativeClustering` |
| pydub/ffmpeg | Audio format conversion | `pydub.AudioSegment.from_file` |
| WeasyPrint | HTML-to-PDF | `weasyprint.HTML` |
| PyMuPDF (fitz) | PDF text extraction | `fitz.open` |
| httpx | External HTTP (D&D Beyond) | `httpx.AsyncClient.get` |
| OpenAI SDK | Image generation API | `talekeeper.services.image_client.AsyncOpenAI` |
| Ollama LLM | Text generation | `talekeeper.services.llm_client.generate` |
| smtplib | SMTP email | `smtplib.SMTP` |
| Filesystem | Audio/image disk I/O | Handled by `tmp_path` fixture |

## New Integration Tests

### recording.py (21% -> ~80%)
- `POST /sessions/{id}/process-audio` SSE: progress + segment + done events
- `POST /sessions/{id}/process-audio` 404/400 error cases
- `GET /sessions/{id}/audio` file streaming and 404
- `POST /sessions/{id}/upload-audio` 400 on non-audio MIME
- `POST /sessions/{id}/upload-audio` replaces existing audio

### transcripts.py (34% -> ~85%)
- `POST /sessions/{id}/retranscribe` SSE: happy path
- `POST /sessions/{id}/retranscribe` 400/404 error cases

### roster.py (50% -> ~85%)
- `POST /roster/{id}/upload-sheet` PDF extraction via mocked LLM
- `POST /roster/{id}/upload-sheet` 400 on non-PDF, empty PDF
- `POST /roster/{id}/import-url` URL fetch + LLM extraction
- `POST /roster/{id}/import-url` D&D Beyond URL pattern
- `POST /roster/{id}/refresh-sheet` re-process and 400 when no data

### images.py (50% -> ~85%)
- `POST /sessions/{id}/generate-image` SSE: with prompt, without prompt
- `POST /sessions/{id}/generate-image` 503 when provider down
- `GET /images/{id}/file` file serving and 404
- `DELETE /sessions/{id}/images` bulk delete

### exports.py (63% -> ~85%)
- `GET /summaries/{id}/export/pdf` with mocked WeasyPrint
- `GET /summaries/{id}/export/pdf?printable=true` printable variant
- `GET /sessions/{id}/export/pov-all` ZIP of POV PDFs
- `POST /summaries/{id}/send-email` via mocked SMTP
- `POST /summaries/{id}/send-email` 400 when SMTP not configured

### speakers.py (67% -> ~85%)
- `POST /sessions/{id}/re-diarize` SSE: happy path
- `POST /sessions/{id}/re-diarize` 409 when session not completed

## New Unit Tests

### diarization.py (22% -> ~60%)
- `diarize()` returns speaker labels for fake embeddings
- `diarize_with_signatures()` matches known signatures
- `run_final_diarization()` with and without voice signatures

### audio.py (expand edge cases)
- `split_audio_to_chunks` with overlapping chunks
- `merge_chunk_files` concatenation
- `compute_primary_zone` boundary deduplication

## Running Tests

```bash
pytest tests/unit -v             # unit layer only
pytest tests/integration -v      # integration layer only
pytest -v                        # everything
pytest --cov=talekeeper          # coverage report
```
