## Context

TaleKeeper currently acquires transcripts exclusively through the audio pipeline: record or upload audio → Whisper transcription → speaker diarization → `completed`. The `transcript_segments` and `speakers` tables are populated only by that pipeline. Sessions without audio cannot reach `completed` status today.

Google Meet's Gemini AI notes feature produces a structured PDF document that includes a transcript section with speaker names, timestamps (`H:MM:SS` or `M:SS`), and dialogue turns. Users who record sessions this way already have a high-quality transcript and want to skip the local ML pipeline to use TaleKeeper's summaries, illustrations, and export features.

Relevant existing infrastructure:
- `pymupdf` (`fitz`) is already a dependency — used elsewhere for PDF work
- `routers/transcripts.py` already owns transcript-related endpoints (`retranscribe`, `re-diarize`)
- `transcript_segments` and `speakers` tables accept rows from any source
- The retranscribe flow clears and rewrites both tables — the import will follow the same pattern
- `python-multipart` is already installed for file uploads

## Goals / Non-Goals

**Goals:**
- Accept a PDF upload for a session and populate `transcript_segments` + `speakers` from it
- Support Gemini's specific PDF format (speaker + timestamp on same line, dialogue below)
- Set session status to `completed` after a successful import
- Show an "Import Transcript" button in the recording UI that works like "Upload Audio"

**Non-Goals:**
- Supporting `.docx`, `.txt`, or other file formats (PDF only for now)
- Parsing non-Gemini transcript layouts (other tools, custom formats)
- Google OAuth or Google Docs API integration — user exports the PDF manually
- Merging an imported transcript with existing segments (import always replaces)
- Extracting audio from the imported document or generating voice signatures

## Decisions

### 1. Use `fitz` (PyMuPDF) for PDF text extraction

**Why:** Already a project dependency; handles Gemini's simple linear PDF layout correctly with `page.get_text()`. No new packages needed.

**Alternative considered:** `pdfplumber` — better for tables and complex layouts but not already installed and unnecessary for this use case.

### 2. Parse with regex line-walking, not a full document parser

**Why:** Gemini's transcript section follows a rigid, predictable pattern: speaker name + 2+ spaces + timestamp on one line, dialogue on the following line(s), blank line separator. A small regex-based state machine is robust enough and avoids pulling in heavy NLP dependencies.

**Regex for speaker-header lines:** `r'^(.+?)\s{2,}(\d+:\d{2}(?::\d{2})?)\s*$'`
- Lazy match for speaker name (shortest string before the double-space gap)
- Timestamp group: `M:SS` or `H:MM:SS`
- Anchored to full line to prevent false positives in dialogue

**Alternative considered:** Heading detection based on font weight from `fitz` block metadata — more robust for unusual PDFs but significantly more complex and untested against the Gemini format.

### 3. Find the "Transcript" section by heading, fall back to full text

**Why:** Gemini PDFs contain preamble (meeting summary, action items) before the transcript. Splitting on the `^Transcript$` heading (case-insensitive) discards noise. If no heading is found, fall back to the full text so the parser still works if Gemini changes its layout.

### 4. Set `end_time = next_turn.start_time`; last segment gets `start_time + 30.0`

**Why:** Imported transcripts have per-turn start timestamps but no explicit end times. Using the next turn's start time is the most accurate estimate. The fixed +30s offset for the final segment is a safe default that avoids a zero-length last segment.

**Alternative considered:** Estimate duration from character count — overly complex for negligible benefit.

### 5. Set both `diarization_label` and `player_name` to the imported speaker name

**Why:** The transcript view joins on `speakers.player_name` and `speakers.character_name` for display. Pre-populating `player_name` with the Gemini name means speaker names appear immediately without requiring manual assignment. Users can still re-assign speakers to roster entries via the existing speaker panel.

**Alternative considered:** Leave `player_name` NULL (only set `diarization_label`) — results in blank speaker names in the transcript view until manually assigned, poor UX.

### 6. New endpoint in `routers/transcripts.py`, not a new router file

**Why:** The import operation is semantically a transcript operation (it creates transcript content). `transcripts.py` already owns the `retranscribe` and `re-diarize` endpoints. Adding one more endpoint there keeps the feature cohesive without adding a new file.

### 7. Synchronous response (no SSE streaming)

**Why:** PDF parsing is fast (pure CPU, no ML). A synchronous JSON response (`{"segments_count": N, "speakers_count": N}`) is simpler than SSE and sufficient — the operation completes in under a second even for long transcripts.

**Alternative considered:** SSE streaming for consistency with other transcript operations — unnecessary complexity when there's nothing meaningful to stream progressively.

## Risks / Trade-offs

- **Gemini format variability** → Mitigation: The fallback (full-text scan when no "Transcript" heading found) and the lazy regex tolerates minor layout variations. Test against real exports before shipping.
- **PDF with images instead of text** → Mitigation: `fitz.get_text()` returns empty string for image-only PDFs; service raises `ValueError("No text found in PDF")` → router returns HTTP 400 with a clear message.
- **Timestamps not present in all Gemini outputs** → Mitigation: `_parse_timestamp` returns `0.0` on failure; all segments default to `start_time = 0.0`, which is a valid value in the DB schema (`NOT NULL` is satisfied). The transcript is still usable.
- **Import overwrites existing audio-derived transcript** → Accepted trade-off, consistent with how retranscribe works. Documented in the UI (button label makes the destructive action clear).
- **No DOCX support** → Users must export from Google Docs as PDF. This is a single click in Google Docs and the format is more predictable than DOCX.

## Migration Plan

No database schema changes. No data migrations required. Rollout is additive:
1. Deploy new endpoint and service
2. Frontend update adds the button

Rollback: remove the endpoint and button — no DB state to undo.

## Open Questions

- Should the import button be hidden/disabled when the session already has a `completed` status (i.e., an existing audio transcript)? Current plan: allow it with a confirmation dialog — same approach as retranscribe.
- Should multi-line dialogue turns be joined with a space or a newline? Current plan: join with a space (consistent with how Whisper outputs single continuous text per segment).
