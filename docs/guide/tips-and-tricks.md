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
    Keyboard shortcuts are disabled when you're typing in a text box or using a dropdown menu.

### Session Status

Sessions move through these stages automatically:

| Status | Meaning |
|--------|---------|
| **Draft** | Session created, no audio yet |
| **Recording** | Microphone is live |
| **Audio Ready** | Audio captured, awaiting processing |
| **Transcribing** | Converting speech to text and identifying speakers |
| **Completed** | Ready for summaries, illustrations, and export |

### Auto-Resume Processing

If you navigate away from a session while it's processing (transcribing, diarizing, etc.), TaleKeeper automatically **resumes tracking progress** when you return. No need to restart — just come back to the session and the progress bar picks up where it left off.

### Language Search by ISO Code

When selecting a language in any language dropdown, you can type an **ISO language code** (e.g., `zh` for Chinese, `he` for Hebrew, `ja` for Japanese) to jump directly to it. The dropdown searches both language names and codes.

### Regenerate Session Name

Completed sessions show a **Regenerate Name** button next to the title. Click it to have the AI craft a new narrative title based on the transcript content — useful if the auto-generated name doesn't capture the session's essence.

### Audio Keeps Playing Across Tabs

You can freely switch between the Recording, Chronicle, Tales, Visions, and Export tabs without interrupting audio playback. Your listening position is preserved — jump to Tales to check a summary, then switch back to Chronicle and the audio is right where you left it.

### Write Your Own Image Prompts

You don't have to use **Generate Scene** before creating an illustration. Type any prompt you like directly into the text area on the Visions tab and click **Generate Image**. Great when you have a specific moment or character pose in mind.

### Edit All Speakers at Once

Instead of editing speakers one by one, click **Edit All** in the speaker panel to open every speaker for editing simultaneously. Your roster members appear as quick-fill buttons — click one to instantly assign both player and character name.

### Availability Warnings

The Tales and Visions tabs automatically check whether your LLM and image providers are reachable when you open them. If something isn't connected, a warning banner appears before you try to generate — saving you from waiting on a request that would fail.

### Optimized for Group Recording

TaleKeeper's recording is tuned for multi-person tabletop sessions. Some automatic audio filtering that normally helps with one-on-one calls is turned off because it can distort recordings when several people speak around the same microphone.

### Stuck Recording Lock

Only one session can record at a time. If you see *"Another session is recording"* but nothing is actually recording, simply **close any old TaleKeeper browser tabs** and try again.

### Best Practices

**Recording Tips:**

- Set the **speaker count** to match your actual party size (including the DM) — it significantly improves speaker detection
- Record in a **quiet environment** when possible — background noise hurts both transcription and diarization
- Use an external microphone if available — laptop mics pick up more noise

**Model Selection:**

- Start with **distil-large-v3** (the default) — it offers excellent accuracy at fast speeds on Apple Silicon
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
| Process All pipeline (one-click transcribe → diarize → summarize → illustrate) | [Recording](recording/index.md) |
| Voice signature confidence threshold | [Voice Signatures](speakers/voice-signatures.md) |
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
| Continue Last Session quick access | [Campaigns](campaigns/index.md) |
| Session content badges (Audio, Transcript, Summary, Images) | [Campaigns](campaigns/index.md) |
| Inline session name editing | [Campaigns](campaigns/index.md) |
| Regenerate session name with AI | [Tips & Tricks](tips-and-tricks.md) |
| Transcript search and filter (text + speaker names) | [Transcription](transcription/index.md) |
| Copy transcript line to clipboard | [Transcription](transcription/index.md) |
| Bidirectional audio ↔ transcript sync | [Transcription](transcription/index.md) |
| Crosstalk segment indicators | [Transcription](transcription/index.md) |
| Voice sample upload from roster | [Roster](campaigns/roster.md) |
| Dark / light theme toggle | [Settings](settings/index.md) |
| Reset to Defaults (preserves API keys) | [Settings](settings/index.md) |
| Auto-resume processing after navigation | [Tips & Tricks](tips-and-tricks.md) |
| Language search by ISO code | [Tips & Tricks](tips-and-tricks.md) |
| Audio keeps playing across tabs | [Tips & Tricks](tips-and-tricks.md) |
| Free-form image prompts (skip Generate Scene) | [Tips & Tricks](tips-and-tricks.md) |
| Edit All speakers with roster quick-fill | [Tips & Tricks](tips-and-tricks.md) |
| LLM / image availability auto-check | [Tips & Tricks](tips-and-tricks.md) |
| Clearing a stuck recording lock | [Tips & Tricks](tips-and-tricks.md) |
| Automatic speaker recognition via voice signatures | [Voice Signatures](speakers/voice-signatures.md) |
| Upload voice sample before first session | [Roster](campaigns/roster.md) |
| Generate voice signatures from labeled session | [Speakers](speakers/index.md) |
| Edit All speakers at once | [Speakers](speakers/index.md) |
| Automatic segment splitting at speaker changes | [Transcription](transcription/index.md) |
| Volume normalization for quiet speakers | [Transcription](transcription/index.md) |
| Color-coded speaker labels | [Transcription](transcription/index.md) |
