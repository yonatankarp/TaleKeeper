## Context

TaleKeeper's frontend is a Svelte 5 app using scoped CSS plus global CSS variables in `app.css` for theming. It supports dark/light themes via a `data-theme` attribute on the root element. There are 19 CSS color variables, a system font stack, and no external UI library. The sidebar, session tabs, and breadcrumbs use hardcoded label strings.

## Goals / Non-Goals

**Goals:**
- Warm up the color palette from cold blue/red-pink to charcoal/gold
- Add a fantasy heading font (Cinzel) for h1-h3 and brand text only
- Place thematic SVG icons at key navigation and tab locations
- Rename "Roster" → "Party", "Transcript" → "Chronicle", "Summaries" → "Tales" in UI labels
- Add subtle gold decorative accents (hover glow, dividers)
- Maintain full dark/light theme support

**Non-Goals:**
- Background textures, images, or corner flourishes
- Adopting a CSS preprocessor or UI component library
- Backend or API changes
- Changing the theme toggle mechanism or adding new themes
- Restructuring component architecture

## Decisions

### 1. Font loading: Google Fonts CDN link in index.html

Load Cinzel via a `<link>` tag in `index.html` with `display=swap` for performance. Add a `--font-heading` CSS variable to `app.css`.

**Alternatives considered:**
- Self-hosting the font: more reliable offline but adds build complexity and font files to the repo. TaleKeeper runs on a local network but still needs internet for initial load anyway (pyannote models, Ollama). CDN is simpler.
- Using `@import` in CSS: blocks rendering. `<link>` with `display=swap` is the standard approach.

### 2. Icons: inline SVG strings in component templates

Place SVG icons directly in the Svelte component markup (Sidebar, SessionDetail) as small inline elements. Each icon is a simple path — no icon library needed.

**Alternatives considered:**
- Icon component with a name prop: adds abstraction for 8 icons. Not worth it at this scale.
- Emoji icons: inconsistent rendering across platforms, limited styling control, can't match gold accent color.
- Icon font (Font Awesome): large dependency for 8 icons. Overkill.

### 3. Color variable replacement: in-place edit of app.css

Replace all CSS variable values in `:root` and `[data-theme="light"]` blocks. The variable names stay the same, so every component that references them picks up the new palette automatically.

No new variables needed except:
- `--font-heading`: for the Cinzel font family
- `--danger`: separate from `--accent` for destructive actions (currently both use `--accent`). Components that use `--accent` for delete/error styling will switch to `--danger`.

### 4. Danger color separation

Currently `--accent` (red-pink) serves double duty as both the brand accent and the danger/error color. With accent shifting to gold, destructive actions need their own variable. Add `--danger: #c2410c` (deep amber-red) and update components that use `--accent` for delete buttons or error states.

**Affected components:** ConfirmDialog (confirm button), campaign/session delete buttons, form validation borders. These currently use `--accent` directly in their scoped styles — each needs updating to `--danger`.

### 5. Terminology: string-level changes only

Rename labels in component templates and the `tabLabels` map in `SessionDetail.svelte`. The tab keys (`transcript`, `summaries`) stay unchanged in code — only the display labels change. Route paths, API endpoints, and internal variable names are unaffected.

The breadcrumb in `App.svelte` and `CampaignDashboard.svelte` that shows "Roster" will change to "Party". The `RosterPage.svelte` filename stays as-is (renaming files is cosmetic churn with no functional benefit).

### 6. Speaker color palette: keep as-is

The existing 8 speaker colors for diarization are already warm and varied. No changes needed — they work well against the new warm background.

## Risks / Trade-offs

- **Google Fonts CDN dependency** → If the CDN is unreachable, headings fall back to serif. The `display=swap` ensures text renders immediately with the fallback and swaps when the font loads. Acceptable for a local-network tool.
- **Gold accent on gold warning** → `--warning` is already `#f0a500` (golden), and `--accent` becomes `#d4a438` (also golden). They are visually distinct (`--warning` is brighter/more orange, `--accent` is more muted/earthy) but worth noting. Warning badges also include text labels, so color alone isn't the only differentiator.
- **Danger color migration** → Splitting `--accent` into `--accent` + `--danger` requires touching scoped styles in several components. Risk of missing a spot where red was intended. Mitigated by searching for all `--accent` usages and reviewing each.
- **Terminology confusion** → Users familiar with "Transcript" and "Summaries" may need a moment to recognize "Chronicle" and "Tales". Both terms are intuitive enough in context, and the tab icons provide additional visual cues.
