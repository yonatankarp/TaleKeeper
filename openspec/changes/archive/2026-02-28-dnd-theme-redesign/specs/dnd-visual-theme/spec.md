## ADDED Requirements

### Requirement: Warm fantasy color palette
The application SHALL use a warm charcoal and gold color palette for the dark theme, replacing the current cold blue and red-pink scheme. The light theme SHALL use warm neutral tones with the same gold accent. Both themes MUST be defined via CSS variables in `app.css`.

Dark theme values:
- `--bg-body`: `#1c1917`, `--bg-surface`: `#292524`, `--bg-input`: `#1c1917`, `--bg-hover`: `#44403c`
- `--border`: `#44403c`, `--accent`: `#d4a438`, `--accent-hover`: `#b8922e`
- `--text`: `#e7e5e4`, `--text-secondary`: `#a8a29e`, `--text-muted`: `#78716c`, `--text-faint`: `#57534e`
- `--danger`: `#c2410c`, `--success`: `#2d6a4f`, `--warning`: `#f0a500`

Light theme values:
- `--bg-body`: `#faf9f7`, `--bg-surface`: `#ffffff`, `--bg-input`: `#f5f5f0`, `--bg-hover`: `#e7e5e4`
- `--border`: `#d6d3d1`, `--accent`: `#b8922e`, `--accent-hover`: `#9a7a24`
- `--text`: `#1c1917`, `--text-secondary`: `#57534e`, `--text-muted`: `#78716c`, `--text-faint`: `#a8a29e`

#### Scenario: Dark theme renders warm charcoal and gold
- **WHEN** the application loads in dark theme
- **THEN** the page background is warm dark (`#1c1917`), surfaces are warm charcoal (`#292524`), and accent elements (active links, primary buttons) are gold (`#d4a438`)

#### Scenario: Light theme renders warm neutrals with gold accent
- **WHEN** the application loads in light theme
- **THEN** the page background is warm off-white (`#faf9f7`), surfaces are white, and accent elements are darker gold (`#b8922e`)

### Requirement: Danger color separated from accent
The application SHALL provide a `--danger` CSS variable distinct from `--accent` for destructive actions. Components that display delete buttons, error states, or destructive confirmation buttons MUST use `--danger` instead of `--accent`.

#### Scenario: Delete button uses danger color
- **WHEN** a delete or destructive action button is rendered
- **THEN** the button uses the `--danger` color (`#c2410c` in dark theme) instead of the gold accent

#### Scenario: Form validation errors use danger color
- **WHEN** a required form field fails validation
- **THEN** the field border uses the `--danger` color

### Requirement: Fantasy heading font
The application SHALL load the Cinzel font from Google Fonts and apply it to all `h1`, `h2`, and `h3` elements and the TaleKeeper brand text. A `--font-heading` CSS variable MUST be defined as `'Cinzel', serif`. Body text, buttons, labels, and form inputs MUST remain in the system font stack.

#### Scenario: Headings render in Cinzel
- **WHEN** any page renders with heading elements (h1, h2, h3)
- **THEN** the headings are displayed in the Cinzel font

#### Scenario: Body text remains in system font
- **WHEN** any page renders body text, button labels, or form inputs
- **THEN** the text is displayed in the system font stack (not Cinzel)

#### Scenario: Font loads with swap display
- **WHEN** the Cinzel font has not yet loaded from Google Fonts CDN
- **THEN** headings render immediately in the serif fallback and swap to Cinzel when loaded (no invisible text flash)

### Requirement: Thematic SVG icons at key UI locations
The application SHALL display inline SVG icons (16-20px, colored with `--accent`) at the following locations:
- TaleKeeper logo in sidebar: D20 die icon
- Campaigns section header in sidebar: shield icon
- Party link in sidebar: crossed swords icon
- Settings link in sidebar: gear icon
- Recording tab label: torch/flame icon
- Chronicle tab label: scroll icon
- Tales tab label: open book icon
- Export tab label: sealed letter icon

Icons MUST be inline SVG elements placed before the label text. Icons MUST use `currentColor` or `var(--accent)` for fill color.

#### Scenario: Sidebar displays thematic icons
- **WHEN** the sidebar renders
- **THEN** the TaleKeeper logo has a D20 die icon, the Campaigns header has a shield icon, the Party link has a crossed swords icon, and the Settings link has a gear icon

#### Scenario: Session tabs display thematic icons
- **WHEN** the session detail tab bar renders
- **THEN** the Recording tab has a torch icon, Chronicle tab has a scroll icon, Tales tab has a book icon, and Export tab has a letter icon

#### Scenario: Icons match accent color
- **WHEN** the theme changes between dark and light
- **THEN** all thematic icons update their color to match the current `--accent` value

### Requirement: Gold decorative accents
The application SHALL add subtle gold decorative effects:
- Cards and surface elements MUST show a subtle gold glow on hover: `box-shadow: 0 0 8px rgba(212, 164, 56, 0.15)`
- The HTML meta theme-color MUST be updated to `#1c1917` to match the new dark background

#### Scenario: Card hover shows gold glow
- **WHEN** the user hovers over a campaign card or session card
- **THEN** a subtle gold box-shadow glow appears around the card

#### Scenario: Meta theme-color matches new palette
- **WHEN** the application loads
- **THEN** the HTML meta theme-color is `#1c1917`
