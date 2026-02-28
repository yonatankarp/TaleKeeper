## 1. Color Palette & CSS Variables

- [x] 1.1 Replace all dark theme CSS variable values in `:root` block of `frontend/src/app.css` with the warm charcoal/gold palette (--bg-body, --bg-surface, --bg-input, --bg-hover, --border, --accent, --accent-hover, --text, --text-secondary, --text-muted, --text-faint, --error-bg, --warning-bg, --badge-dark, --btn-blue)
- [x] 1.2 Add `--danger: #c2410c` to `:root` and `--danger: #b91c1c` to `[data-theme="light"]` block
- [x] 1.3 Replace all light theme CSS variable values in `[data-theme="light"]` block with warm neutral palette
- [x] 1.4 Update meta theme-color in `frontend/index.html` from `#1a1a2e` to `#1c1917`

## 2. Danger Color Migration

- [x] 2.1 Audit all components using `--accent` for destructive/error purposes by searching for `--accent` in scoped styles
- [x] 2.2 Update `ConfirmDialog.svelte` confirm button to use `--danger` instead of `--accent`
- [x] 2.3 Update delete/destructive button styles in `CampaignList.svelte`, `CampaignDashboard.svelte`, `RosterPage.svelte`, and `SummarySection.svelte` to use `--danger`
- [x] 2.4 Update form validation error border styles in `CampaignList.svelte` and `CampaignDashboard.svelte` to use `--danger`

## 3. Typography

- [x] 3.1 Add Google Fonts `<link>` tag for Cinzel (weights 400, 700) with `display=swap` to `frontend/index.html`
- [x] 3.2 Add `--font-heading: 'Cinzel', serif;` variable to `:root` in `app.css`
- [x] 3.3 Add `font-family: var(--font-heading);` rule for `h1, h2, h3` selectors in `app.css`
- [x] 3.4 Add `font-family: var(--font-heading);` to the `.logo` class in `Sidebar.svelte`

## 4. Thematic SVG Icons — Sidebar

- [x] 4.1 Add D20 die inline SVG icon before "TaleKeeper" text in the `.logo` button in `Sidebar.svelte`
- [x] 4.2 Add shield inline SVG icon before "Campaigns" section header in `Sidebar.svelte`
- [x] 4.3 Add crossed swords inline SVG icon before "Party" link in `CampaignDashboard.svelte`
- [x] 4.4 Add gear inline SVG icon before "Settings" link in `Sidebar.svelte`

## 5. Thematic SVG Icons — Session Tabs

- [x] 5.1 Add torch/flame inline SVG icon to the Recording tab label in `SessionDetail.svelte`
- [x] 5.2 Add scroll inline SVG icon to the Chronicle tab label in `SessionDetail.svelte`
- [x] 5.3 Add open book inline SVG icon to the Tales tab label in `SessionDetail.svelte`
- [x] 5.4 Add sealed letter inline SVG icon to the Export tab label in `SessionDetail.svelte`

## 6. Terminology Renames

- [x] 6.1 Rename tab label "Transcript" to "Chronicle" and "Summaries" to "Tales" in the `tabLabels` map in `SessionDetail.svelte`
- [x] 6.2 Rename "Player Roster" heading to "Party" in `RosterPage.svelte`
- [x] 6.3 Rename "Roster" button to "Party" in `CampaignDashboard.svelte`
- [x] 6.4 Rename "Roster" breadcrumb labels to "Party" in `App.svelte` (both occurrences on lines 55 and 57)
- [x] 6.5 Rename "Remove Roster Entry" dialog title and "from the roster" message to "Remove Party Member" and "from the party" in `RosterPage.svelte`
- [x] 6.6 Rename "No players in the roster yet" empty state message to "No players in the party yet" in `RosterPage.svelte`
- [x] 6.7 Rename "Loading roster..." spinner text to "Loading party..." in `RosterPage.svelte`

## 7. Decorative Accents

- [x] 7.1 Add gold hover glow (`box-shadow: 0 0 8px rgba(212, 164, 56, 0.15)`) to `.card` elements on hover in components that render campaign/session cards (`CampaignList.svelte`, `CampaignDashboard.svelte`)
- [x] 7.2 Update recording badge pulse color from red-pink to amber-red (`--danger`) in `SessionDetail.svelte`
