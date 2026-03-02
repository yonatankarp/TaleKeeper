## 1. Restructure Test Directories

- [ ] 1.1 Create `tests/unit/services/`, `tests/integration/db/`, `tests/integration/routers/` directories with `__init__.py` files
- [ ] 1.2 Move `tests/services/*` to `tests/unit/services/`
- [ ] 1.3 Move `tests/db/*` to `tests/integration/db/`
- [ ] 1.4 Move `tests/routers/*` to `tests/integration/routers/`
- [ ] 1.5 Clean up empty old directories
- [ ] 1.6 Verify all existing tests still pass after the move

## 2. SSE Test Infrastructure

- [ ] 2.1 Add `parse_sse_events(text: str) -> list[dict]` helper to `tests/conftest.py` that parses SSE text into `{event, data}` dicts with automatic JSON parsing

## 3. Integration Tests — Recording (21% → ~80%)

- [ ] 3.1 Add `test_process_audio_happy_path` — mocks transcribe_chunked, audio_to_wav, run_final_diarization; verifies progress, segment, phase, done SSE events
- [ ] 3.2 Add `test_process_audio_session_not_found` — verifies 404
- [ ] 3.3 Add `test_process_audio_no_audio` — verifies 400 when session has no audio file
- [ ] 3.4 Add `test_download_audio` — file streaming with correct content
- [ ] 3.5 Add `test_download_audio_no_audio` — 404 when no audio path set
- [ ] 3.6 Add `test_download_audio_file_missing` — 404 when audio_path points to nonexistent file
- [ ] 3.7 Add `test_upload_audio_invalid_mime` — 400 for non-audio MIME types
- [ ] 3.8 Add `test_upload_audio_replaces_existing` — second upload clears old segments and speakers

## 4. Integration Tests — Transcripts (34% → ~85%)

- [ ] 4.1 Add `test_retranscribe_happy_path` — mocks transcribe_chunked, webm_to_wav, run_final_diarization; verifies progress, segment, done SSE events
- [ ] 4.2 Add `test_retranscribe_no_audio` — 400 when session has no audio
- [ ] 4.3 Add `test_retranscribe_session_not_found` — 404

## 5. Integration Tests — Speakers (67% → ~85%)

- [ ] 5.1 Add `test_re_diarize_happy_path` — mocks run_final_diarization, audio_to_wav; verifies phase, done SSE events
- [ ] 5.2 Add `test_re_diarize_session_not_completed` — 409 when session status is not 'completed'
- [ ] 5.3 Add `test_re_diarize_no_audio` — 400 when no audio file

## 6. Integration Tests — Images (50% → ~85%)

- [ ] 6.1 Add `test_generate_image_with_prompt` — mocks image generation; verifies craft_scene NOT called when prompt provided
- [ ] 6.2 Add `test_generate_image_crafts_scene_when_no_prompt` — verifies craft_scene IS called when no prompt
- [ ] 6.3 Add `test_generate_image_session_not_found` — 404
- [ ] 6.4 Add `test_get_image_file_not_found` — 404
- [ ] 6.5 Add `test_delete_all_session_images` — bulk delete returns count

## 7. Integration Tests — Roster (50% → ~85%)

- [ ] 7.1 Add `test_upload_sheet_pdf` — mocks fitz + LLM; verifies PDF text extracted and description generated
- [ ] 7.2 Add `test_upload_sheet_non_pdf` — 400 for non-PDF files
- [ ] 7.3 Add `test_import_url` — mocks httpx + LLM; verifies URL content fetched and description generated
- [ ] 7.4 Add `test_refresh_sheet_no_data` — 400 when no sheet data stored

## 8. Integration Tests — Exports (63% → ~85%)

- [ ] 8.1 Add `test_export_pdf_printable` — verifies printable PDF generation with mocked WeasyPrint
- [ ] 8.2 Add `test_export_pov_all_zip` — verifies ZIP with POV PDFs
- [ ] 8.3 Add `test_export_pov_all_no_summaries` — 404 when no POV summaries
- [ ] 8.4 Add `test_send_email` — mocks smtplib; verifies email sent
- [ ] 8.5 Add `test_send_email_smtp_not_configured` — 400 when no SMTP settings

## 9. Unit Tests — Diarization (22% → ~60%)

- [ ] 9.1 Add `test_diarize_with_num_speakers` — verifies AgglomerativeClustering called with `n_clusters`
- [ ] 9.2 Add `test_diarize_without_num_speakers` — verifies `distance_threshold` used instead

## 10. Unit Tests — Audio Service (edge cases)

- [ ] 10.1 Add `test_split_audio_to_chunks_multiple` — verifies long audio produces multiple overlapping chunks
- [ ] 10.2 Add `test_compute_primary_zone_middle_chunk` — verifies both edges trimmed for middle chunks

## 11. Verification

- [ ] 11.1 Run `pytest -v` — all tests pass
- [ ] 11.2 Run `pytest --cov=talekeeper --cov-report=term-missing` — verify coverage improvement toward ~80%
