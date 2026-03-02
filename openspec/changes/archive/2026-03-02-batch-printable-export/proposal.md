## Why

The existing `export/pov-all` endpoint only exports POV summaries, and the resulting PDFs include hero images which aren't suitable for printing. DMs need a single action to export all session summaries (both full chronicle and POV) as printer-friendly PDFs — no hero images, clean layout — in a single ZIP download.

## What Changes

- **Rename and extend the batch export endpoint**: `GET /api/sessions/{id}/export/pov-all` becomes `GET /api/sessions/{id}/export/summaries-all`, removing the POV-only filter to include all summary types (full + POV).
- **Add printable mode**: A `printable: bool = False` query parameter that, when true, omits the hero image from each PDF for clean printing.
- **ZIP file naming**: Full summaries named `session-chronicle.pdf`, POV summaries named `{character-name}-pov.pdf`. ZIP filename changed to `summaries.zip`.
- **Frontend update**: Replace the "Export All POV Summaries (ZIP)" button with a top-level "Export All Printable (ZIP)" button visible when any summaries exist, pointing to the new endpoint with `printable=true`.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `export-and-sharing`: The batch export endpoint changes from POV-only to all summaries, adds a printable mode that omits hero images, and uses updated file naming in the ZIP. The frontend button is updated to use the new endpoint.

## Impact

- **Backend**: `src/talekeeper/routers/exports.py` — endpoint renamed, SQL filter removed, printable parameter added, ZIP naming updated
- **Frontend**: `frontend/src/components/ExportSection.svelte` — button URL and label updated, moved to top-level position
- **No new dependencies**
- **No database changes**
