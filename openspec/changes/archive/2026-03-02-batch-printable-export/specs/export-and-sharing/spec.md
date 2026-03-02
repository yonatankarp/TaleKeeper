## MODIFIED Requirements

### Requirement: PDF export of summaries
The system SHALL support a `printable` mode for PDF exports. When `printable` is true, the PDF MUST omit the hero image section, producing a clean layout suitable for printing. The `printable` parameter MUST default to false (hero image included when available).

#### Scenario: Export printable PDF without hero image
- **WHEN** the DM exports a summary as PDF with `printable=true`
- **THEN** the PDF renders with D&D theming but without the hero image section, regardless of whether session images exist

### Requirement: Batch export of all summaries
The system SHALL allow the DM to export all summaries for a session (both full and POV) in a single action via `GET /api/sessions/{id}/export/summaries-all`, producing one PDF per summary in a ZIP file. The endpoint MUST accept a `printable: bool` query parameter (default false). Full summary PDFs MUST be named `session-chronicle.pdf`. POV summary PDFs MUST be named `{character-name}-pov.pdf` (lowercase, spaces replaced with hyphens, fallback to `unknown` if no character name). The ZIP file MUST be named `summaries.zip`. If no summaries exist for the session, the endpoint MUST return 404.

#### Scenario: Batch export all summaries as printable ZIP
- **WHEN** the DM clicks "Export All Printable (ZIP)" for a session with a full summary and 3 POV summaries
- **THEN** a ZIP named `summaries.zip` is downloaded containing `session-chronicle.pdf` and 3 character-named POV PDFs, all without hero images

#### Scenario: Batch export with no summaries
- **WHEN** the DM requests batch export for a session with no summaries
- **THEN** the system returns a 404 error with "No summaries found"

#### Scenario: Frontend batch export button visibility
- **WHEN** a session has any summaries (full or POV)
- **THEN** a top-level "Export All Printable (ZIP)" button is visible in the export section
