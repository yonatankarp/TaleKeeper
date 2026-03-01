## Context

The current PDF export uses a minimal HTML template (`PDF_TEMPLATE` in `exports.py`) — Georgia serif, plain `<h1>`, a meta `<div>`, and the summary content dumped with `white-space: pre-wrap`. The same template is used for both full summaries and POV summaries. There is no connection between session images and exports.

The app already uses WeasyPrint (>=63) for PDF generation, which supports CSS `@page` rules, `@font-face` with remote URLs, CSS gradients, pseudo-elements, and base64 image embedding. The D&D visual theme spec defines Cinzel as the heading font and a warm gold/parchment palette — these should carry into the PDF.

## Goals / Non-Goals

**Goals:**
- Replace the plain PDF template with a D&D-themed design that feels like a fantasy artifact
- Differentiate POV exports (journal style) from full summary exports (chronicle style)
- Embed the latest session image as a hero at the top of the PDF
- Render summary text as proper paragraphs with typographic polish (drop cap, dividers)

**Non-Goals:**
- Custom raster texture images for parchment (CSS gradients only)
- Bundling fonts locally (use Google Fonts CDN, WeasyPrint fetches at render time)
- Changing the transcript export (stays plain text)
- Changing email export content or any API contracts
- Multi-page image galleries (one hero image only)

## Decisions

### 1. Single template function, not separate template strings

**Decision**: Replace the single `PDF_TEMPLATE` string with a `_build_pdf_html()` function that accepts the summary dict, content HTML, and optional image bytes, and returns the complete HTML string. The function branches on `summary["type"]` to produce POV vs. full styling.

**Why**: A function allows conditional sections (image present/absent, POV vs. full title) without duplicating large template blocks. Python f-strings with a helper function are cleaner than trying to cram conditionals into a format string.

**Alternative considered**: Two separate template strings (`POV_PDF_TEMPLATE`, `FULL_PDF_TEMPLATE`). Rejected because 90% of the CSS and structure is shared — duplication would be a maintenance burden.

### 2. Fonts via Google Fonts CSS import

**Decision**: Use `@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Cinzel+Decorative:wght@700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap')` in the `<style>` block.

**Why**: WeasyPrint fetches remote CSS and font files at render time. This keeps the codebase clean — no font files to vendor. Cinzel for headings and Crimson Text for body match the app's existing visual language.

**Trade-off**: Requires internet at PDF generation time. Acceptable because the app already requires network for LLM calls. Falls back to serif if offline.

### 3. CSS-only parchment and decorations

**Decision**: All visual theming is pure CSS — no image assets.

- **Parchment background**: Radial gradient from `#f4e8d1` (center) to `#e8d5b0` (edges) on `@page`
- **Decorative border**: Double-line border on the content area using `box-shadow` (inset) and `border`, in warm gold (`#8b7335`)
- **Side ornaments**: CSS `::before` / `::after` pseudo-elements on the content wrapper using unicode ornamental characters (❧, ◆, ⚜) in gold, positioned along the left and right margins
- **Section dividers**: Centered `<div class="divider">` between paragraphs using `─── ◆ ───` style, rendered via CSS `::before` content
- **Drop cap**: `p:first-of-type::first-letter` with Cinzel Decorative, enlarged, floated left

**Why**: No asset management, no file path issues, works everywhere WeasyPrint runs. CSS gradients produce a convincing parchment look.

### 4. Image embedding via base64 data URI

**Decision**: Read the image file from disk (`file_path` from `session_images` table), base64-encode it, and embed as `<img src="data:image/png;base64,...">` in the HTML.

**Why**: WeasyPrint renders HTML from a string — there's no base URL for relative paths. Data URIs are the standard approach. PNG images from the image generator are typically 500KB–2MB, which is fine for embedding.

**Alternative considered**: Using `base_url` parameter in WeasyPrint to resolve file paths. Rejected because it ties the template to the server's filesystem layout and is fragile.

### 5. Latest image selection query

**Decision**: Add a helper `_get_latest_session_image(session_id) -> bytes | None` that queries:
```sql
SELECT file_path FROM session_images
WHERE session_id = ? ORDER BY generated_at DESC LIMIT 1
```
Then reads the file from disk. Returns `None` if no images exist or the file is missing.

**Why**: Simple, predictable. The user said "if many have been generated, take the latest." One query, one file read, graceful fallback.

### 6. Content rendering — text to HTML paragraphs

**Decision**: Add a `_content_to_html(text: str) -> str` helper that:
1. Splits on double newlines (`\n\n`) to get paragraphs
2. Wraps each in `<p>...</p>`
3. Replaces `---` or `***` lines with `<div class="divider"></div>`

**Why**: The LLM generates plain text with paragraph breaks as double newlines. Converting to `<p>` tags enables proper CSS paragraph spacing, drop caps on the first paragraph, and section dividers. This is a minimal transformation — no markdown parser needed.

### 7. POV vs. Full summary differentiation

**Decision**: The template function adds a CSS class to the body (`class="pov"` or `class="full"`) and adjusts the header:

| Aspect | POV | Full |
|--------|-----|------|
| Title | "The Journal of [Character Name]" | "Session Chronicle" |
| Subtitle | Session name · Campaign · Date | Session name · Campaign · Date |
| Body class | `pov` | `full` |
| First-letter style | Cinzel Decorative, slightly italic feel | Cinzel Decorative, bold |
| Footer | "As recorded by [Player Name]" | "Generated by TaleKeeper" |

**Why**: Minimal divergence — same template, same CSS, just different content and a class toggle for the few styling differences.

## Risks / Trade-offs

**[Google Fonts requires network]** → WeasyPrint falls back to generic serif if fonts can't be fetched. The PDF still looks decent, just not with the fantasy fonts. This is an acceptable degradation for an offline-first tool that already needs network for LLM/image generation.

**[Large images increase PDF size]** → A 1–2MB PNG base64-encoded adds ~1.3–2.7MB to the PDF. For a single-session export this is fine. The ZIP of all POVs repeats the same image per character — could be 10MB+ for 4 characters. Acceptable for local use.

**[Unicode ornaments may render differently across systems]** → WeasyPrint uses its own rendering pipeline, so the PDF output is consistent regardless of the viewer's system. The ornamental characters (❧, ◆, ⚜) are in standard Unicode blocks supported by common fonts.

**[Template complexity in a Python string]** → The HTML/CSS template will be significantly larger (~100-150 lines of CSS). Keeping it as a string constant in `exports.py` is adequate for a single template. If it grows further in the future, it could be extracted to an HTML file — but that's not needed now.
