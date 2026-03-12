## 1. Backend Service

- [ ] 1.1 Create `src/talekeeper/services/transcript_import.py` with `ParsedTurn` dataclass
- [ ] 1.2 Implement `_parse_timestamp(ts: str) -> float` (supports `M:SS` and `H:MM:SS`)
- [ ] 1.3 Implement `_extract_pdf_text(pdf_bytes: bytes) -> str` using `fitz`; raise `ValueError` if empty
- [ ] 1.4 Implement `_find_transcript_section(full_text: str) -> str` — split on `^Transcript$` heading, fall back to full text
- [ ] 1.5 Implement `parse_gemini_transcript(text: str) -> list[ParsedTurn]` — line-walking parser with speaker-header regex; assign `end_time = next.start_time`, last segment gets `+30.0`
- [ ] 1.6 Implement `async import_transcript_from_pdf(session_id: int, pdf_bytes: bytes) -> dict` — orchestrates extract → parse → DB writes → status update; raise `ValueError` if no turns found

## 2. Backend Endpoint

- [ ] 2.1 Add `File, UploadFile` to the existing `fastapi` import in `src/talekeeper/routers/transcripts.py`
- [ ] 2.2 Add `POST /api/sessions/{session_id}/import-transcript` endpoint — validate PDF extension, check session exists (404), delegate to service, return `{"segments_count": N, "speakers_count": N}`

## 3. Backend Tests

- [ ] 3.1 Create `tests/unit/services/test_transcript_import.py` with timestamp parsing tests (`M:SS`, `H:MM:SS`, `0:00`, invalid input)
- [ ] 3.2 Add parser tests: 3-turn happy path (speaker names, start times, end-time chain), preamble stripping, empty input, single-turn last-segment estimate, multi-line dialogue join
- [ ] 3.3 Add DB integration tests (using `db` fixture, patch `_extract_pdf_text`): import clears existing segments, session status set to `completed`, speaker rows created, invalid session raises `ValueError`

## 4. Frontend API

- [ ] 4.1 Add `importTranscriptPdf(sessionId: number, file: File)` to `frontend/src/lib/api.ts` — `FormData` POST, same pattern as `uploadAudio`, returns `{ segments_count, speakers_count }`

## 5. Frontend UI

- [ ] 5.1 Add `importingTranscript = $state(false)` and `pdfFileInput` ref to `frontend/src/components/RecordingControls.svelte`
- [ ] 5.2 Extend the `busy` derived to include `importingTranscript`
- [ ] 5.3 Add hidden `<input type="file" accept=".pdf">` and `handlePdfSelected` handler that calls `importTranscriptPdf` then `onStatusChange()`
- [ ] 5.4 Add "Import Transcript" button (after "Upload Audio", before "Process All") and importing progress banner

## 6. Transcript Empty State

- [ ] 6.1 Update the empty-state message in `frontend/src/components/TranscriptView.svelte` to mention importing as an option alongside recording and re-transcribing
