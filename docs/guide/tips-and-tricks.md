# Tips & Tricks

## Secrets of the Craft

A collection of power-user tips, hidden features, and best practices to get the most out of TaleKeeper.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ++1++ | Switch to Recording tab |
| ++2++ | Switch to Chronicle (Transcript) tab |
| ++3++ | Switch to Tales (Summaries) tab |
| ++4++ | Switch to Visions (Illustrations) tab |
| ++5++ | Switch to Export tab |
| ++enter++ | Save session name (while editing) |
| ++escape++ | Cancel session name edit |

!!! note
    Keyboard shortcuts are disabled when you're typing in an input field, textarea, or dropdown.

### Session Status Lifecycle

Sessions move through these states automatically:

```
draft → recording → transcribing → completed
```

| Status | Meaning |
|--------|---------|
| **Draft** | Session created, no audio yet |
| **Recording** | Microphone is live |
| **Transcribing** | Processing audio (transcription + diarization) |
| **Completed** | Ready for summaries, illustrations, and export |

### Best Practices

**Recording Tips:**

- Set the **speaker count** to match your actual party size (including the DM) — it significantly improves speaker detection
- Record in a **quiet environment** when possible — background noise hurts both transcription and diarization
- Use an external microphone if available — laptop mics pick up more noise

**Model Selection:**

- Start with **medium** (the default) — it's the best balance of speed and accuracy for most sessions
- Try **large-v3** for important sessions, heavily accented speech, or mixed-language games
- Use **tiny** or **base** only for quick tests or if your machine struggles with larger models

**Speaker Management:**

- **Name speakers early** — before generating summaries, so the AI knows character names
- **Fill in your roster** with descriptions — this enriches both summaries and illustrations
- If diarization split one person into two speakers, **merge them** before generating summaries

**Summaries & Illustrations:**

- **Longer sessions produce better summaries** — the AI has more material to work with
- **Generate illustrations after summaries** — the AI uses summary content to craft better scenes
- **Character descriptions matter** — the more detail in your roster, the better your illustrations

### Multi-Language Support

TaleKeeper supports 98 languages across the entire pipeline:

- **Transcription** — Whisper recognizes speech in all supported languages
- **Summaries** — generated in the session's configured language
- **Session names** — auto-generated in the correct language
- **Scene descriptions** — image prompts respect the source language context

Set the language at campaign level (applies to new sessions) or override per-session.

### All Hidden Features at a Glance

| Feature | Where to Find It |
|---------|-----------------|
| Live transcription during recording | [Settings](settings/index.md) |
| D&D Beyond character import | [Roster](campaigns/roster.md) |
| PDF character sheet extraction | [Roster](campaigns/roster.md) |
| Generic URL character import | [Roster](campaigns/roster.md) |
| Sheet refresh / re-extraction | [Roster](campaigns/roster.md) |
| Session auto-renumbering | [Campaigns](campaigns/index.md) |
| Speaker count override at recording end | [Recording](recording/index.md) |
| Retranscription with different settings | [Retranscription](transcription/retranscription.md) |
| Speaker merging | [Merging](speakers/merging.md) |
| Re-diarization without re-transcription | [Speakers](speakers/index.md) |
| Voice signatures | [Voice Signatures](speakers/voice-signatures.md) |
| POV character journal entries | [Journals](summaries/pov-journals.md) |
| Auto session naming | [Summaries](summaries/index.md) |
| Scene description editing | [Illustrations](illustrations/index.md) |
| Character appearance in illustrations | [Illustrations](illustrations/index.md) |
| Printable PDF mode | [PDF Export](export/index.md) |
| Batch ZIP export | [PDF Export](export/index.md) |
| Hero image in PDFs | [PDF Export](export/index.md) |
| Email sharing | [Email](export/email-sharing.md) |
