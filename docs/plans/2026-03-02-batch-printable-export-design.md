# Batch Printable Export

## Summary

Extend the existing `export/pov-all` endpoint to export all session summaries (full + POV) as printable PDFs in a ZIP.

## Changes

### Backend: `src/talekeeper/routers/exports.py`

- Rename `GET /api/sessions/{session_id}/export/pov-all` to `GET /api/sessions/{session_id}/export/summaries-all`
- Add `printable: bool = False` query parameter
- Remove `WHERE su.type = 'pov'` filter — fetch all summaries for the session
- Pass `printable` flag to `_build_pdf_html`
- When `printable=True`, skip hero image (consistent with single-PDF export behavior)
- File naming in ZIP:
  - Full summaries: `session-chronicle.pdf`
  - POV summaries: `{character-name}-pov.pdf`
- ZIP filename: `summaries.zip`

### Frontend: `frontend/src/components/ExportSection.svelte`

- Update button URL from `export/pov-all` to `export/summaries-all?printable=true`
- Rename button text to "Export All Printable (ZIP)"
- Move button to top-level position (not nested under POV section) since it covers all summaries
- Show button when any summaries exist (not just POV)
