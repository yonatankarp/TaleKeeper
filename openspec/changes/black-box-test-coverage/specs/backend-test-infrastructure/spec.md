## MODIFIED Requirements

### Requirement: Test directory structure
The test suite SHALL be organized into two explicit layers: `tests/unit/` for function-level tests where all dependencies are mocked, and `tests/integration/` for HTTP-path tests using a real temp SQLite database with only external I/O mocked. Service tests SHALL reside in `tests/unit/services/`. Database tests SHALL reside in `tests/integration/db/`. Router tests SHALL reside in `tests/integration/routers/`.

#### Scenario: Unit tests isolated from external dependencies
- **WHEN** tests in `tests/unit/` are executed
- **THEN** all external dependencies (Whisper, SpeechBrain, pydub, WeasyPrint, httpx, OpenAI, Ollama, smtplib) are mocked, and no real I/O occurs

#### Scenario: Integration tests use real database
- **WHEN** tests in `tests/integration/` are executed
- **THEN** a real temporary SQLite database is used for all database operations, and only external I/O boundaries are mocked

#### Scenario: Tests discoverable by layer
- **WHEN** `pytest tests/unit -v` is run
- **THEN** only unit-layer tests are executed
- **AND** **WHEN** `pytest tests/integration -v` is run
- **THEN** only integration-layer tests are executed

## ADDED Requirements

### Requirement: SSE event parsing for tests
The test suite SHALL provide a shared `parse_sse_events(text: str) -> list[dict]` helper in `tests/conftest.py` that parses Server-Sent Events formatted text into a list of `{event, data}` dictionaries. The `data` field SHALL be automatically parsed as JSON when valid, or kept as a string otherwise. SSE comments (lines starting with `:`) SHALL be ignored.

#### Scenario: Parse SSE response from streaming endpoint
- **WHEN** a test receives a streaming response with SSE-formatted text
- **THEN** `parse_sse_events()` returns a list of event dicts with `event` and `data` keys, with JSON data automatically deserialized

### Requirement: SSE endpoint test coverage
The test suite SHALL include integration tests for all SSE streaming endpoints: process-audio, retranscribe, re-diarize, and generate-image. Each endpoint SHALL have at least a happy-path test verifying the expected SSE event sequence and error-case tests verifying correct HTTP status codes.

#### Scenario: SSE happy-path tests verify event sequence
- **WHEN** SSE integration tests run for a streaming endpoint
- **THEN** the test verifies the expected event types (progress, segment, phase, done) appear in the response

#### Scenario: SSE error-case tests verify status codes
- **WHEN** SSE integration tests run with invalid input (missing session, missing audio, wrong status)
- **THEN** the test verifies the correct HTTP error status code (400, 404, 409) is returned
