## Why

The current PDF export produces plain, unstyled documents — just a title, meta line, and text blob in Georgia serif. For a D&D session tool, the exported PDFs should feel like fantasy artifacts: parchment-toned pages, decorative borders, fantasy typography, and session artwork. POV summaries in particular are the primary export players receive, and they should read like in-world journal entries worth keeping.

## What Changes

- **D&D-themed PDF template**: Replace the plain `PDF_TEMPLATE` with a rich HTML/CSS template featuring parchment background (CSS gradient), fantasy fonts (Cinzel headers, Crimson Text body), decorative side borders, ornamental dividers, and a drop cap on the first paragraph.
- **Session hero image in PDFs**: When a session has generated images, embed the most recent one as a full-width hero image at the top of the PDF.
- **POV journal styling**: POV summary PDFs use a personal journal aesthetic — "The Journal of [Character Name]" as the title, first-person narrative formatting with elegant paragraph spacing.
- **Full summary chronicle styling**: Full session summary PDFs use a chronicle/record aesthetic — "Session Chronicle" as the title, third-person narrative formatting.
- **Paragraph-aware content rendering**: Parse summary text into proper `<p>` tags (splitting on double newlines) instead of using `white-space: pre-wrap`, enabling drop caps, proper spacing, and section dividers.
- **Image query in export endpoints**: The PDF export endpoints query `session_images` for the latest image and read it from disk for base64 embedding in the HTML.

## Capabilities

### New Capabilities

_(none — this modifies existing export behavior)_

### Modified Capabilities

- `export-and-sharing`: PDF export requirements change significantly — PDFs now include D&D fantasy theming (fonts, colors, decorative borders, parchment background), embedded session images, distinct styling for POV vs. full summaries, and paragraph-aware content rendering. The API surface and export formats remain the same (still PDF files from the same endpoints).

## Impact

- **Backend**: `src/talekeeper/routers/exports.py` — `PDF_TEMPLATE` replaced with a much richer template; `_get_summary_with_meta` and export endpoints updated to also fetch the latest session image and base64-encode it for embedding.
- **No new dependencies**: WeasyPrint already supports CSS `@font-face` with Google Fonts URLs, `@page` rules, gradients, and base64 image embedding. Cinzel and Crimson Text are loaded via Google Fonts CDN at PDF render time.
- **No API changes**: Same endpoints, same response format. The PDFs just look much better.
- **No frontend changes**: The export buttons and UI remain identical.
