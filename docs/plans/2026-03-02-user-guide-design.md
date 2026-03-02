# TaleKeeper User Guide — Design Document

## Overview

A comprehensive, D&D-themed user guide for TaleKeeper built with MkDocs + Material for MkDocs. Organized workflow-first to match the natural user journey from campaign creation through export.

## Audience

End users — DMs and players using TaleKeeper to record and manage D&D sessions. Not technical/developer focused.

## Tone & Style

- D&D-themed flavor text for section intros (e.g., Recording = "Roll for Initiative")
- Clear, usable instructions underneath the flavor — never obscure meaning
- Screenshot placeholders (`[Screenshot: description]`) where visuals would help
- Material for MkDocs admonitions for tips, hidden features, and warnings

## Technology

- **MkDocs** with **Material for MkDocs** theme
- Multi-page documentation site
- Dark mode support, search, admonitions, tabs

## Site Structure

```
docs/
├── index.md                    # Welcome / What is TaleKeeper
├── getting-started/
│   ├── index.md                # Installation & first launch
│   └── setup-wizard.md         # First-run setup (data dir, LLM config)
├── campaigns/
│   ├── index.md                # Creating & managing campaigns
│   └── roster.md               # Character roster, D&D Beyond import, PDF sheets
├── recording/
│   ├── index.md                # Live recording workflow
│   └── uploading.md            # Uploading pre-recorded audio
├── transcription/
│   ├── index.md                # How transcription works, model sizes
│   └── retranscription.md      # Re-running with different settings
├── speakers/
│   ├── index.md                # Speaker assignment & editing
│   ├── merging.md              # Merging duplicate speakers
│   └── voice-signatures.md     # Voice enrollment & identification
├── summaries/
│   ├── index.md                # Full session summaries
│   └── pov-journals.md         # Character POV journal entries
├── illustrations/
│   └── index.md                # Scene image generation
├── export/
│   ├── index.md                # PDF export (themed & printable)
│   ├── text-export.md          # Plaintext & transcript export
│   └── email-sharing.md        # Email summaries to players
├── settings/
│   └── index.md                # All settings: LLM, image provider, SMTP, whisper
└── tips-and-tricks.md          # Hidden features, power-user tips, keyboard shortcuts
```

## Page Content Outlines

### Welcome (index.md)
- What TaleKeeper does in one paragraph
- Feature highlights (recording, transcription, AI summaries, illustrations, PDF export)
- Quick "your first session in 5 minutes" overview linking to Getting Started

### Getting Started
- Prerequisites (ffmpeg, Ollama optional)
- Installation steps
- Setup wizard walkthrough: data directory picker, LLM configuration
- Health check indicators

### Campaigns & Roster
- Creating campaigns with language & speaker count defaults
- Campaign dashboard overview
- Hidden: Session auto-numbering and renumbering when start number changes
- Roster: adding characters manually
- Hidden: D&D Beyond import — paste URL, pulls class/race/appearance
- Hidden: PDF character sheet upload — LLM extracts visual descriptions
- Hidden: Generic URL import for any web character sheet
- Hidden: Sheet refresh to re-extract descriptions

### Recording & Upload
- Live recording workflow with timer
- Hidden: Live transcription toggle (transcribes as you record)
- Hidden: Speaker count override at end of recording
- Uploading pre-recorded audio files
- Audio replacement behavior

### Transcription
- How it works (Whisper, on-device, no cloud)
- Model size trade-offs (tiny=fast, large=accurate)
- Language selection
- Hidden: Retranscription with different model/language/speaker count
- Hidden: Chunked processing with overlap deduplication for long sessions

### Speakers
- Assigning names to detected speakers
- Roster suggestions dropdown
- Bulk reassignment
- Hidden: Speaker merging (combine duplicate speakers atomically)
- Hidden: Re-diarization without re-transcribing
- Voice signatures: what they are, how enrollment works

### Summaries
- Generating full session recaps
- Hidden: POV journal entries — first-person character perspective
- Hidden: Character descriptions from roster included in generation
- Hidden: Auto session naming from transcript content
- Regenerating & editing summaries

### Illustrations
- How scene generation works (LLM crafts prompt → image model generates)
- Hidden: Character appearances from roster for visual consistency
- Hidden: Scene description editing before generation
- Hidden: Multiple variations from same scene
- SSE progress tracking

### Export
- PDF export: D&D-themed parchment with medieval fonts
- Hidden: Printable mode (white background)
- Hidden: Hero image inclusion (most recent illustration)
- Hidden: Batch ZIP export of all summaries
- Hidden: POV PDFs named by character
- Text & transcript export with timestamps
- Hidden: Email sharing with SMTP

### Settings
- Data directory
- LLM provider config (Ollama, OpenAI-compatible)
- Image provider config
- SMTP email setup
- Whisper model & live transcription toggle
- Health check buttons

### Tips & Tricks
- Keyboard shortcuts
- Multi-language support across the full pipeline
- Session status lifecycle
- Best practices (model size recommendations, speaker count tips)

## Hidden Features to Surface

These are non-obvious capabilities that the guide should highlight with admonitions:

1. **Live transcription during recording** — toggle in settings
2. **D&D Beyond character import** — paste URL in roster
3. **PDF character sheet extraction** — upload PDF, LLM reads it
4. **Generic URL character import** — any web character sheet
5. **Sheet refresh** — re-extract descriptions from stored URLs
6. **Speaker merging** — combine duplicate speakers
7. **Re-diarization** — re-run speaker detection without re-transcribing
8. **Voice signatures** — speaker enrollment across sessions
9. **POV journal summaries** — first-person character narratives
10. **Auto session naming** — AI-generated catchy titles
11. **Scene description editing** — tweak image prompts before generation
12. **Character appearance in illustrations** — roster descriptions used for visual consistency
13. **Printable PDF mode** — white background for printing
14. **Batch ZIP export** — all summaries in one download
15. **Email sharing** — send summaries directly to players
16. **Session renumbering** — changing start number cascades to all sessions
17. **Speaker count override** — set at end of recording
18. **Retranscription** — re-run with different model/language/speakers
