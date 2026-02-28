## Why

TaleKeeper is a D&D session recording tool, but its UI looks like a generic SaaS app — cold blue tones, system fonts, no thematic personality. Adding subtle fantasy touches makes the experience feel like it belongs in the D&D world, reinforcing the app's identity without sacrificing usability.

## What Changes

- **Color palette**: Shift from cold dark-blue/red-pink to warm charcoal/gold across both dark and light themes
- **Typography**: Add Cinzel (Google Fonts) for headings and brand text; body stays system font
- **Icons**: Add inline SVG icons at key navigation and tab locations (d20, shield, scroll, etc.)
- **Terminology**: Rename "Roster" → "Party", "Transcript" → "Chronicle", "Summary/Summaries" → "Tale/Tales"
- **Decorative touches**: Gold card hover glow, gold accent dividers, warm recording indicator colors

## Capabilities

### New Capabilities
- `dnd-visual-theme`: Color palette (CSS variables for both themes), Cinzel heading font, inline SVG icons at key UI locations, gold decorative accents (hover glow, dividers)

### Modified Capabilities
- `session-tabs`: Tab labels change — "Transcript" tab becomes "Chronicle", "Summaries" tab becomes "Tales"
- `campaign-management`: Sidebar and breadcrumb label "Roster" becomes "Party"; recording badge pulse color shifts from red-pink to amber/red

## Impact

- **Frontend CSS**: `app.css` — all CSS variable values change (colors, font family addition)
- **Frontend HTML**: `index.html` — Google Fonts `<link>` tag added
- **Components**: `Sidebar.svelte`, `SessionDetail.svelte`, `RosterPage.svelte`, `TranscriptView.svelte`, `SummarySection.svelte` — label text changes and SVG icon additions
- **No backend changes**: Purely frontend/cosmetic
- **No new dependencies**: Google Fonts loaded via CDN, icons are inline SVG
- **No API changes**: All terminology is UI-label-only; API routes/fields unchanged
