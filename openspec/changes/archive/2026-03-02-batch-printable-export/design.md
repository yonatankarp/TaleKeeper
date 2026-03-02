## Context

The app has a `GET /api/sessions/{id}/export/pov-all` endpoint that exports only POV summaries as a ZIP of PDFs. Each PDF includes the D&D-themed template with hero images. There is no way to export all summary types together, and no way to produce printer-friendly PDFs without the large hero images.

The frontend has an "Export All POV Summaries (ZIP)" button nested inside the POV summaries section, only visible when POV summaries exist.

## Goals / Non-Goals

**Goals:**
- Allow batch export of all summaries (full + POV) in a single ZIP
- Support a printable mode that omits hero images for clean printing
- Update the frontend to use the new endpoint with sensible defaults

**Non-Goals:**
- Changing the individual PDF export endpoint
- Adding new export formats (only PDF in ZIP)
- Modifying the D&D template styling itself

## Decisions

### 1. Extend existing endpoint rather than add a new one

**Decision**: Rename `export/pov-all` to `export/summaries-all` and remove the `WHERE su.type = 'pov'` SQL filter. Add `printable: bool = False` query parameter.

**Why**: The new endpoint is a strict superset of the old one — it can still export only POV summaries if desired. Renaming avoids having two similar endpoints and makes the API clearer.

**Alternative considered**: Adding a separate `export/summaries-all` endpoint alongside the existing one. Rejected because the old endpoint becomes redundant.

### 2. Printable mode via query parameter

**Decision**: When `printable=True`, set `image_bytes = None` before building PDFs, which causes `_build_pdf_html` to omit the hero image section.

**Why**: Reuses the existing template logic — `_build_pdf_html` already handles the case where `image_bytes` is `None`. No template changes needed.

### 3. ZIP file naming convention

**Decision**: Full summaries are named `session-chronicle.pdf`, POV summaries are named `{character-name}-pov.pdf` (lowercase, spaces replaced with hyphens). ZIP filename is `summaries.zip`.

**Why**: Clear differentiation between summary types. Character names in filenames make it easy for the DM to distribute files to players.

## Risks / Trade-offs

**[Breaking change to endpoint URL]** → The old `export/pov-all` URL stops working. Acceptable because this is a local-only app with no external API consumers. The frontend is updated simultaneously.

**[Unknown character name fallback]** → If a POV summary has no associated speaker with a character name, the filename falls back to `unknown-pov.pdf`. Edge case that only occurs with orphaned data.
