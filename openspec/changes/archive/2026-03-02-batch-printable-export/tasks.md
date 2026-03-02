## 1. Backend — Extend the Export Endpoint

- [x] 1.1 Rename `export_all_pov` function to `export_all_summaries` in `src/talekeeper/routers/exports.py`
- [x] 1.2 Change route path from `export/pov-all` to `export/summaries-all`
- [x] 1.3 Add `printable: bool = False` query parameter
- [x] 1.4 Remove `AND su.type = 'pov'` from the SQL query to fetch all summary types
- [x] 1.5 Set `image_bytes = None` when `printable=True`, pass `printable=printable` to `_build_pdf_html`
- [x] 1.6 Update ZIP file naming: `session-chronicle.pdf` for full summaries, `{char-name}-pov.pdf` for POV summaries
- [x] 1.7 Change ZIP filename to `summaries.zip` and error message to "No summaries found"

## 2. Backend — Add Tests

- [x] 2.1 Add `test_export_summaries_all` — verifies ZIP contains both `session-chronicle.pdf` and `{char}-pov.pdf`
- [x] 2.2 Add `test_export_summaries_all_printable` — verifies printable CSS styling is applied
- [x] 2.3 Add `test_export_summaries_all_empty` — verifies 404 when no summaries exist

## 3. Frontend — Update Export Button

- [x] 3.1 Add top-level "Batch Export" section in `ExportSection.svelte` visible when any summaries exist
- [x] 3.2 New button calls `export/summaries-all?printable=true` with label "Export All Printable (ZIP)"
- [x] 3.3 Remove the old "Export All POV Summaries (ZIP)" button from the POV section
