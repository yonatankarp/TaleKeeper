# TaleKeeper User Guide Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a comprehensive, D&D-themed user guide as a MkDocs Material site covering all TaleKeeper features workflow-first.

**Architecture:** MkDocs site with Material theme in `docs/guide/` directory. Each page covers one workflow step. Hidden features surfaced via Material admonitions. Screenshot placeholders for future visual additions.

**Tech Stack:** MkDocs, mkdocs-material, Python (pip install)

---

### Task 1: Set Up MkDocs Project

**Files:**
- Create: `mkdocs.yml`
- Create: `docs/guide/index.md` (placeholder)

**Step 1: Install MkDocs and Material theme**

Run: `.venv/bin/pip install mkdocs mkdocs-material`

**Step 2: Create mkdocs.yml at project root**

```yaml
site_name: TaleKeeper
site_description: Record, transcribe, and summarize your D&D sessions
site_url: ""

theme:
  name: material
  palette:
    - scheme: slate
      primary: deep orange
      accent: amber
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
    - scheme: default
      primary: deep orange
      accent: amber
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
  features:
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.tabs.link
  icon:
    logo: material/book-open-variant

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - attr_list
  - md_in_html
  - toc:
      permalink: true

docs_dir: docs/guide

nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/index.md
    - Setup Wizard: getting-started/setup-wizard.md
  - Campaigns:
    - Managing Campaigns: campaigns/index.md
    - Character Roster: campaigns/roster.md
  - Recording:
    - Live Recording: recording/index.md
    - Uploading Audio: recording/uploading.md
  - Transcription:
    - How It Works: transcription/index.md
    - Retranscription: transcription/retranscription.md
  - Speakers:
    - Speaker Assignment: speakers/index.md
    - Merging Speakers: speakers/merging.md
    - Voice Signatures: speakers/voice-signatures.md
  - Summaries:
    - Session Recaps: summaries/index.md
    - Character Journals: summaries/pov-journals.md
  - Illustrations: illustrations/index.md
  - Export:
    - PDF Export: export/index.md
    - Text & Transcript: export/text-export.md
    - Email Sharing: export/email-sharing.md
  - Settings: settings/index.md
  - Tips & Tricks: tips-and-tricks.md
```

**Step 3: Create placeholder index**

Create `docs/guide/index.md` with just a `# TaleKeeper` heading so the build works.

**Step 4: Verify MkDocs builds**

Run: `cd /Users/yonatankarp-rudin/Projects/TaleKeeper && .venv/bin/mkdocs build`
Expected: Build succeeds (warnings about missing pages are OK for now)

**Step 5: Commit**

```bash
git add mkdocs.yml docs/guide/index.md
git commit -m "docs: set up mkdocs with material theme for user guide"
```

---

### Task 2: Write Home Page (index.md)

**Files:**
- Modify: `docs/guide/index.md`

**Step 1: Write the welcome page**

```markdown
# Welcome to TaleKeeper

**Your party's adventures, preserved forever.**

TaleKeeper records your D&D sessions, transcribes the audio, identifies who's speaking, and uses AI to generate narrative summaries, character journal entries, and scene illustrations — all running on your own machine. No cloud services required.

## What Can TaleKeeper Do?

| Feature | Description |
|---------|-------------|
| **Record** | Capture your session audio live, or upload pre-recorded files |
| **Transcribe** | On-device speech-to-text in 98 languages using Whisper |
| **Identify Speakers** | Automatically detect and label who's talking |
| **Summarize** | AI-generated session recaps and character POV journals |
| **Illustrate** | Generate scene artwork from your session's key moments |
| **Export** | D&D-themed PDFs, plaintext, and email sharing |

## Your First Session in 5 Minutes

1. **[Install TaleKeeper](getting-started/index.md)** and run the setup wizard
2. **[Create a campaign](campaigns/index.md)** for your adventure
3. **[Record a session](recording/index.md)** — hit the red button and play
4. **[Read your transcript](transcription/index.md)** — TaleKeeper handles the rest
5. **[Generate summaries](summaries/index.md)** — get a narrative recap instantly

!!! tip "Hidden Depths"
    TaleKeeper has far more features than meet the eye. Look for these callouts throughout the guide — they reveal powerful capabilities you might otherwise miss.

[Get Started :material-arrow-right:](getting-started/index.md){ .md-button .md-button--primary }
```

**Step 2: Verify build**

Run: `.venv/bin/mkdocs build`
Expected: Clean build

**Step 3: Commit**

```bash
git add docs/guide/index.md
git commit -m "docs: write user guide home page"
```

---

### Task 3: Write Getting Started Pages

**Files:**
- Create: `docs/guide/getting-started/index.md`
- Create: `docs/guide/getting-started/setup-wizard.md`

**Step 1: Write installation page**

`docs/guide/getting-started/index.md`:

```markdown
# Installation

## Preparing Your Keep

Before TaleKeeper can chronicle your adventures, you'll need a few things in place.

### Prerequisites

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **ffmpeg** — Required for audio processing
- **Ollama** *(optional)* — For AI summaries and image generation

=== "macOS"

    ```bash
    brew install ffmpeg
    brew install ollama  # optional, for AI features
    ```

=== "Linux"

    ```bash
    sudo apt install ffmpeg
    # For Ollama, see https://ollama.ai
    ```

### Install TaleKeeper

```bash
pip install talekeeper
```

### Launch

```bash
talekeeper serve
```

This starts the server at `http://localhost:8000` and opens your browser automatically.

!!! info "Command Options"
    | Flag | Description |
    |------|-------------|
    | `--host <address>` | Bind to a specific address (default: `127.0.0.1`) |
    | `--port <number>` | Use a different port (default: `8000`) |
    | `--reload` | Auto-reload on code changes (development) |
    | `--no-browser` | Don't open the browser on startup |

### Optional: Set Up Ollama

If you want AI-powered summaries, character journals, and scene illustrations:

```bash
ollama serve
ollama pull llama3.1:8b        # For text generation
ollama pull x/flux2-klein:9b   # For image generation (macOS only)
```

!!! note "No Ollama? No Problem"
    Recording, transcription, and speaker identification work entirely without Ollama or any LLM. You only need an AI provider for summaries, session naming, and illustration generation.

[Screenshot: TaleKeeper home screen after first launch]

Next: [Run the Setup Wizard →](setup-wizard.md)
```

**Step 2: Write setup wizard page**

`docs/guide/getting-started/setup-wizard.md`:

```markdown
# The Setup Wizard

## Charting Your Course

On your first launch, TaleKeeper greets you with a setup wizard to configure the essentials. You can always re-run it later from the Settings page.

[Screenshot: Setup wizard modal overlay]

### Step 1: Data Directory

Choose where TaleKeeper stores your recordings, transcripts, and summaries.

[Screenshot: Data directory step with browse button]

!!! tip "Backup Tip"
    As long as this folder exists, all your data is safe. Back it up regularly to preserve your campaign archives.

- Click **Browse** to open your system's folder picker
- Or type a path directly into the field
- The status indicator shows ✓ when the directory is valid

### Step 2: LLM Provider

Connect an AI provider for summaries and session naming.

[Screenshot: LLM provider configuration step]

| Field | Description | Example |
|-------|-------------|---------|
| Base URL | Your provider's API endpoint | `http://localhost:11434/v1` |
| API Key | Authentication key (optional for Ollama) | — |
| Model | Which model to use | `llama3.1:8b` |

!!! info "Supported Providers"
    TaleKeeper works with any **OpenAI-compatible** API:

    - **Ollama** (local, free) — recommended for getting started
    - **OpenAI** — use your API key with models like `gpt-4o`
    - **Any OpenAI-compatible service** — LM Studio, vLLM, etc.

### Step 3: Image Generation (Optional)

Configure a provider for AI scene illustrations.

[Screenshot: Image generation configuration step]

The setup is identical to the LLM provider — Base URL, API Key, and Model.

!!! warning "macOS Note"
    Ollama image generation (e.g., `x/flux2-klein:9b`) currently only works on macOS. For other platforms, use a cloud provider like OpenAI (`dall-e-3`).

### Finishing Up

- Click **Re-check** to test your connections (status indicators update)
- Click **Get Started** when the LLM shows connected
- Or click **Continue Anyway** to skip AI features for now

!!! tip "Hidden Feature"
    You can re-run the setup wizard at any time from the **Settings** page — look for the "Run Setup Wizard" button at the bottom.

Next: [Create Your First Campaign →](../campaigns/index.md)
```

**Step 3: Verify build**

Run: `.venv/bin/mkdocs build`
Expected: Clean build

**Step 4: Commit**

```bash
git add docs/guide/getting-started/
git commit -m "docs: write getting started and setup wizard pages"
```

---

### Task 4: Write Campaign & Roster Pages

**Files:**
- Create: `docs/guide/campaigns/index.md`
- Create: `docs/guide/campaigns/roster.md`

**Step 1: Write campaigns page**

`docs/guide/campaigns/index.md`:

```markdown
# Managing Campaigns

## Founding Your Company

A **campaign** is your top-level container — think of it as one continuous adventure or storyline. Each campaign holds sessions, a character roster, and shared settings.

### Creating a Campaign

[Screenshot: Campaign creation form]

| Field | Description | Default |
|-------|-------------|---------|
| Name | Your campaign's title | — |
| Description | A brief synopsis | — |
| Language | Primary spoken language | English |
| Number of Speakers | Expected party size (1–10) | 5 |

!!! tip "Speaker Count Matters"
    The speaker count helps TaleKeeper's diarization (speaker detection) algorithm. Set it close to your actual party size for the best results — it's not a hard limit, just a hint.

### The Campaign Dashboard

[Screenshot: Campaign dashboard with sessions grid]

Your dashboard shows:

- All sessions in chronological order
- Session count, total recorded time, and most recent session date
- Quick access to create a new session

### Editing Campaign Settings

Click on the campaign name or settings to modify:

- **Name and description** — update anytime
- **Language** — changes the default for new sessions
- **Speaker count** — adjusts diarization defaults
- **Session start number** — for campaigns that didn't start at session 1

!!! tip "Hidden Feature: Session Renumbering"
    Changing the **session start number** automatically renumbers all existing sessions and updates any sessions that still have the default "Session N" name. Useful if you're importing a campaign that started as session 15 in a larger arc.

### Deleting a Campaign

Deleting a campaign permanently removes all its sessions, recordings, transcripts, summaries, and images. This cannot be undone.

[Screenshot: Campaign delete confirmation dialog]

Next: [Set Up Your Character Roster →](roster.md)
```

**Step 2: Write roster page**

`docs/guide/campaigns/roster.md`:

```markdown
# Character Roster

## Assembling the Party

The **roster** tracks your campaign's characters — their names, players, and visual descriptions. This information enriches summaries, illustrations, and speaker identification.

[Screenshot: Roster page with character entries]

### Adding Characters Manually

Click **Add Character** and fill in:

| Field | Description |
|-------|-------------|
| Player Name | The real-world player |
| Character Name | Their in-game character |
| Description | Visual appearance and notable features |

!!! info "Why Descriptions Matter"
    Character descriptions are used in two powerful ways:

    1. **Summaries** — the AI references them for accurate character portrayal
    2. **Illustrations** — scene images include character appearances for visual consistency

### Importing from D&D Beyond

!!! tip "Hidden Feature"
    Paste a **D&D Beyond character URL** and TaleKeeper automatically pulls the character's class, race, appearance, and equipment details.

[Screenshot: D&D Beyond import with URL field]

1. Open your character on D&D Beyond
2. Copy the character page URL
3. Paste it into the **Sheet URL** field on the roster entry
4. TaleKeeper fetches and extracts a visual description via AI

### Uploading a PDF Character Sheet

!!! tip "Hidden Feature"
    Upload a **PDF character sheet** and the AI will extract a visual description from it — works with official sheets, homebrew, and any format.

[Screenshot: PDF upload on roster entry]

### Importing from Any URL

!!! tip "Hidden Feature"
    Have a character on a different platform? Paste **any web URL** containing character information and TaleKeeper will attempt to extract relevant details.

### Refreshing Descriptions

!!! tip "Hidden Feature"
    Click **Refresh** on a roster entry to re-fetch and re-extract the description from the stored URL. Useful after character changes or level-ups.

### Active vs Inactive Characters

Toggle characters as **active** or **inactive**. Inactive characters are hidden from speaker suggestions but preserved in the roster for reference.

Next: [Record Your First Session →](../recording/index.md)
```

**Step 3: Verify build & commit**

Run: `.venv/bin/mkdocs build`

```bash
git add docs/guide/campaigns/
git commit -m "docs: write campaigns and roster guide pages"
```

---

### Task 5: Write Recording Pages

**Files:**
- Create: `docs/guide/recording/index.md`
- Create: `docs/guide/recording/uploading.md`

**Step 1: Write live recording page**

`docs/guide/recording/index.md`:

```markdown
# Live Recording

## Roll for Initiative

The **Recording** tab (keyboard shortcut: ++1++) is where your session begins. TaleKeeper captures audio directly from your microphone and processes it when you stop.

[Screenshot: Recording tab in idle state]

### Starting a Recording

1. Navigate to your session's **Recording** tab
2. Set the **Speakers** count (1–10) to match your party size
3. Click **Start Recording** (the red button)

[Screenshot: Recording in progress with timer]

!!! note "Microphone Permissions"
    Your browser will ask for microphone access the first time. TaleKeeper needs this to capture audio — it never leaves your machine.

### During Recording

While recording, you'll see:

- A **pulsing red dot** with elapsed time (HH:MM:SS)
- **Pause** and **Stop** buttons
- A recording badge in the session header visible from any tab

You can:

- **Pause** — temporarily halt recording, then **Resume**
- **Stop** — end the recording and begin processing

!!! tip "Hidden Feature: Live Transcription"
    Enable **live transcription** in Settings to see preview transcript segments appear in real time as you record. These are preliminary — the final transcript will be more accurate with proper speaker labels.

    [Screenshot: Settings with live transcription toggle]

### After Stopping

When you stop recording, TaleKeeper automatically:

1. Merges audio chunks into a single file
2. Converts to the format needed for transcription
3. Runs speech-to-text (Whisper)
4. Runs speaker diarization (identifies who spoke when)
5. Generates an AI session name (if an LLM is configured)

A progress bar shows the current phase:

- **"Uploading..."** — finalizing audio
- **"Transcribing X / Y chunks — ~N min remaining"** — speech recognition in progress
- **"Assigning speakers..."** — diarization running

[Screenshot: Processing progress bar with ETA]

!!! tip "Hidden Feature: Speaker Count Override"
    You can adjust the speaker count right before stopping — useful if unexpected guests joined or someone left early.

!!! warning "One at a Time"
    Only one session can be recorded at a time. If another session is recording, you'll see a message indicating it's locked.

Next: [Or Upload Pre-Recorded Audio →](uploading.md)
```

**Step 2: Write uploading page**

`docs/guide/recording/uploading.md`:

```markdown
# Uploading Audio

## Recovered Scrolls

Already have a recording from another device? Upload it directly instead of recording live.

### How to Upload

1. Go to the **Recording** tab (++1++)
2. Click **Upload Audio**
3. Select your audio file

[Screenshot: Upload button on recording tab]

TaleKeeper accepts common audio formats and automatically converts them for processing.

### What Happens Next

After upload, the same processing pipeline runs automatically:

1. Audio conversion (mono, 16kHz WAV)
2. Transcription
3. Speaker diarization
4. Auto session naming

!!! warning "Replacing Audio"
    Uploading new audio to a session that already has a recording will **replace** the previous audio and clear the existing transcript and speaker assignments. Summaries and images are preserved.

Next: [Understanding Your Transcript →](../transcription/index.md)
```

**Step 3: Verify build & commit**

Run: `.venv/bin/mkdocs build`

```bash
git add docs/guide/recording/
git commit -m "docs: write recording and upload guide pages"
```

---

### Task 6: Write Transcription Pages

**Files:**
- Create: `docs/guide/transcription/index.md`
- Create: `docs/guide/transcription/retranscription.md`

**Step 1: Write transcription overview**

`docs/guide/transcription/index.md`:

```markdown
# Transcription

## The Scribe's Art

TaleKeeper uses **Whisper**, an on-device speech recognition model, to transcribe your recordings. Everything runs locally — your audio never leaves your machine.

### Viewing the Transcript

Switch to the **Chronicle** tab (++2++) to see your full transcript.

[Screenshot: Chronicle tab with transcript segments]

Each segment shows:

- **Timestamp** — when the words were spoken
- **Speaker** — who said it (assigned by diarization)
- **Text** — what was said

!!! tip "Click to Seek"
    Click any transcript segment to jump to that moment in the audio player. Useful for reviewing specific moments.

### Whisper Model Sizes

The model size affects speed and accuracy. Configure it in **Settings**.

| Model | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| `tiny` | Fastest | Lower | Quick previews, testing |
| `base` | Fast | Fair | Short sessions |
| `small` | Moderate | Good | Most sessions |
| **`medium`** | Slower | **Very Good** | **Recommended default** |
| `large-v3` | Slowest | Best | Critical recordings, accented speech |

!!! info "Long Sessions"
    For recordings over 5 minutes, TaleKeeper automatically splits audio into chunks with overlapping segments to ensure nothing is missed at boundaries. You don't need to do anything — it's handled transparently.

### Language Support

TaleKeeper supports **98 languages** out of the box. Set the language at the campaign or session level, and transcription, summaries, and session names will all respect it.

Common languages: English, Spanish, French, German, Japanese, Korean, Chinese, Hebrew, Arabic, Portuguese, Italian, Russian, and [many more](../tips-and-tricks.md).

Next: [Re-run Transcription →](retranscription.md)
```

**Step 2: Write retranscription page**

`docs/guide/transcription/retranscription.md`:

```markdown
# Retranscription

## A Second Reading

!!! tip "Hidden Feature"
    Not satisfied with the transcript? You can **re-run transcription** with different settings — no need to re-record.

### When to Retranscribe

- The transcript has errors and you want to try a **larger model**
- You initially used the wrong **language** setting
- The **speaker count** was off and diarization suffered
- You want to try a different combination of settings

### How to Retranscribe

[Screenshot: Retranscription controls on session page]

1. Select a different **Whisper model** size
2. Optionally change the **language**
3. Optionally adjust the **speaker count**
4. Click **Retranscribe**

!!! warning "This Replaces the Existing Transcript"
    Retranscription clears the current transcript and speaker assignments, then generates new ones. Summaries and images are not affected.

### Progress Tracking

Retranscription streams progress via the same phases:

- Transcription chunk progress with ETA
- Speaker diarization
- Auto session naming (if the name was still generic)

Next: [Assign Speaker Names →](../speakers/index.md)
```

**Step 3: Verify build & commit**

Run: `.venv/bin/mkdocs build`

```bash
git add docs/guide/transcription/
git commit -m "docs: write transcription guide pages"
```

---

### Task 7: Write Speaker Pages

**Files:**
- Create: `docs/guide/speakers/index.md`
- Create: `docs/guide/speakers/merging.md`
- Create: `docs/guide/speakers/voice-signatures.md`

**Step 1: Write speaker assignment page**

`docs/guide/speakers/index.md`:

```markdown
# Speaker Assignment

## Naming the Voices

After transcription, TaleKeeper's diarization identifies distinct speakers and labels them as "Player 1", "Player 2", etc. Your job is to assign real names.

[Screenshot: Speaker panel with unnamed speakers]

### Assigning Names

For each detected speaker:

1. Set the **Player Name** (the real person)
2. Set the **Character Name** (their in-game persona)

!!! tip "Roster Suggestions"
    If you've set up your [Character Roster](../campaigns/roster.md), a dropdown suggests names from your campaign's active roster members. No need to type — just select.

[Screenshot: Speaker dropdown with roster suggestions]

### Reassigning Segments

Sometimes diarization assigns a segment to the wrong speaker. You can fix this:

1. Find the segment in the **Chronicle** tab
2. Use the speaker dropdown on that segment to reassign it

!!! tip "Hidden Feature: Bulk Reassign"
    Select multiple segments and reassign them all to the same speaker in one action. Saves time when diarization consistently misidentified one voice.

### Re-Diarization

!!! tip "Hidden Feature"
    If speaker detection was poor, you can **re-run diarization** without re-transcribing. This keeps your transcript text intact but reassigns speaker labels from scratch.

    This is faster than full retranscription and useful when:

    - The speaker count was wrong
    - Speakers were sitting too close together
    - Background noise confused the algorithm

Next: [Merge Duplicate Speakers →](merging.md)
```

**Step 2: Write merging page**

`docs/guide/speakers/merging.md`:

```markdown
# Merging Speakers

## Joining Forces

!!! tip "Hidden Feature"
    Sometimes diarization creates two entries for the same person (e.g., "Player 1" and "Player 3" are both the DM). **Speaker merging** combines them into one.

### How to Merge

[Screenshot: Speaker merge controls]

1. Identify the duplicate speakers in the speaker panel
2. Select the **source** speaker (the one to merge away)
3. Select the **target** speaker (the one to keep)
4. Confirm the merge

### What Happens

The merge is **atomic** — it happens in a single transaction:

- All transcript segments from the source are reassigned to the target
- Voice signatures from the source are cleaned up
- The source speaker is deleted
- The target speaker retains their name and all segments

!!! note "This Cannot Be Undone"
    Speaker merging permanently combines two speakers. If you're unsure, check the transcript segments first to verify they're really the same person.

Next: [Voice Signatures →](voice-signatures.md)
```

**Step 3: Write voice signatures page**

`docs/guide/speakers/voice-signatures.md`:

```markdown
# Voice Signatures

## A Familiar Voice

!!! tip "Hidden Feature"
    TaleKeeper can create **voice signatures** — audio fingerprints for each speaker that persist across sessions within a campaign.

### What Are Voice Signatures?

A voice signature is a mathematical representation of someone's voice, generated from labeled audio in your sessions. Once created, these signatures are stored with the character roster and can be used to improve speaker identification in future sessions.

### How It Works

1. **Record a session** and assign speaker names as usual
2. **Generate voice signatures** — TaleKeeper extracts speaker embeddings from the labeled audio
3. The signatures are stored with the corresponding **roster entry**

### Voice Signature Details

Each signature stores:

- The audio embedding (speaker "fingerprint")
- Which session it was generated from
- The number of audio samples used

!!! info "Campaign-Wide"
    Voice signatures are tied to **roster entries**, meaning they persist across all sessions in a campaign. The more sessions you label, the more data TaleKeeper has to work with.

Next: [Generate Summaries →](../summaries/index.md)
```

**Step 4: Verify build & commit**

Run: `.venv/bin/mkdocs build`

```bash
git add docs/guide/speakers/
git commit -m "docs: write speaker management guide pages"
```

---

### Task 8: Write Summary Pages

**Files:**
- Create: `docs/guide/summaries/index.md`
- Create: `docs/guide/summaries/pov-journals.md`

**Step 1: Write summaries overview**

`docs/guide/summaries/index.md`:

```markdown
# Session Summaries

## The Chronicler's Quill

The **Tales** tab (++3++) is where AI transforms your raw transcript into a polished narrative recap of your session.

[Screenshot: Tales tab with generated summary]

### Generating a Summary

1. Switch to the **Tales** tab
2. Click **Generate Summary**
3. Wait for the AI to process your transcript

The summary appears as a narrative recap — written in prose, covering the key events, decisions, and dramatic moments of your session.

!!! info "How It Works"
    TaleKeeper sends your transcript (or a representative sample for very long sessions) to your configured LLM along with character descriptions from your roster. The AI generates a narrative summary in the session's language.

### Editing Summaries

Click on a summary to edit its content directly. Changes are saved when you finish editing.

### Regenerating

Not happy with the result? Click **Regenerate** to create a new summary. This replaces the existing one.

!!! tip "Hidden Feature: Auto Session Naming"
    When a summary is generated, TaleKeeper also creates a **catchy session title** based on the content. Sessions with generic "Session N" names get upgraded to something like "The Siege of Blackmoor" or "Betrayal at the Crossroads". Custom names you've set are never overwritten.

!!! tip "Character Descriptions Enhance Summaries"
    If you've filled in character descriptions in your [roster](../campaigns/roster.md), the AI uses them when writing summaries — leading to more accurate character portrayals and richer narrative detail.

### Multiple Summaries

You can generate multiple summaries per session. Each is stored independently and can be exported separately.

Next: [Character Journal Entries →](pov-journals.md)
```

**Step 2: Write POV journals page**

`docs/guide/summaries/pov-journals.md`:

```markdown
# Character Journals

## Through Their Eyes

!!! tip "Hidden Feature"
    Beyond the standard session recap, TaleKeeper generates **point-of-view journal entries** — first-person narratives written from each character's perspective.

[Screenshot: POV journal entries grouped by character]

### What Are POV Journals?

Each named character in your session gets their own journal entry, written as if they were recounting the session's events in their own words. It's like reading a diary entry from each party member.

### How They're Generated

POV journals are generated alongside full summaries. When you click **Generate Summary**, TaleKeeper creates:

1. **One full session recap** — third-person narrative
2. **One journal entry per named character** — first-person perspective

### Example

> *"We arrived at the ruins before dawn. I warned the others about the wards I sensed, but Theron charged ahead as usual. When the shadows came alive, I was ready — my shield held while Elara found the binding circle..."*

### Requirements

- Speakers must have **character names** assigned (not just "Player 1")
- An **LLM provider** must be configured
- Character descriptions from the roster enhance the writing quality

Next: [Generate Scene Illustrations →](../illustrations/index.md)
```

**Step 3: Verify build & commit**

Run: `.venv/bin/mkdocs build`

```bash
git add docs/guide/summaries/
git commit -m "docs: write summaries and POV journals guide pages"
```

---

### Task 9: Write Illustrations Page

**Files:**
- Create: `docs/guide/illustrations/index.md`

**Step 1: Write illustrations page**

`docs/guide/illustrations/index.md`:

```markdown
# Scene Illustrations

## Visions of Adventure

The **Visions** tab (++4++) lets you generate AI artwork depicting dramatic moments from your session.

[Screenshot: Visions tab with generated scene images]

### How It Works

Image generation is a two-step process:

1. **Scene Crafting** — an LLM reads your transcript and crafts a vivid scene description focusing on one dramatic moment
2. **Image Generation** — the description is sent to an image model to create the artwork

### Generating an Image

1. Switch to the **Visions** tab
2. Click **Generate Image**
3. Watch the progress phases:
    - *"Crafting scene..."* — AI is writing the scene description
    - *"Generating image..."* — image model is rendering
    - *Done!* — image appears in the gallery

[Screenshot: Image generation progress with phase indicator]

!!! tip "Hidden Feature: Edit the Scene Description"
    Before generation begins, you can **edit the scene description** that the AI crafted. This lets you steer the image toward a specific moment or adjust details.

!!! tip "Hidden Feature: Character Appearance Consistency"
    If your [character roster](../campaigns/roster.md) has visual descriptions, they're included in the scene prompt. This means your characters look consistent across different illustrations — Theron always has his red cloak, Elara always carries her silver staff.

### Creating Variations

!!! tip "Hidden Feature"
    Click **Generate Image** again to create a different scene or variation. Each generation is independent — you can build a gallery of multiple moments from the same session.

### Managing Images

- Images are displayed newest-first in the gallery
- Delete individual images or clear all images for a session
- The most recent image is used as the **hero image** in PDF exports

### Requirements

- An **image generation provider** must be configured (see [Settings](../settings/index.md))
- An **LLM provider** is needed for scene description crafting
- Works with Ollama (macOS only for images), OpenAI DALL-E, ComfyUI, Stable Diffusion, or any OpenAI-compatible image API

Next: [Export Your Work →](../export/index.md)
```

**Step 2: Verify build & commit**

Run: `.venv/bin/mkdocs build`

```bash
git add docs/guide/illustrations/
git commit -m "docs: write illustrations guide page"
```

---

### Task 10: Write Export Pages

**Files:**
- Create: `docs/guide/export/index.md`
- Create: `docs/guide/export/text-export.md`
- Create: `docs/guide/export/email-sharing.md`

**Step 1: Write PDF export page**

`docs/guide/export/index.md`:

```markdown
# PDF Export

## Bound in Parchment

The **Export** tab (++5++) lets you create beautiful, D&D-themed PDF documents from your summaries.

[Screenshot: Export tab with PDF options]

### Session Chronicle PDF

Export your full session summary as a themed PDF featuring:

- **Parchment background** with warm radial gradient
- **Medieval typography** — Cinzel headings and Crimson Text body
- **Decorative borders** with ornamental fleurons (✦)
- **Drop cap** styling on the first paragraph
- **Ornamental dividers** (◆) between sections
- Campaign name, session name, and date in the header

[Screenshot: Sample PDF with parchment theme]

### Character Journal PDFs

Each POV journal entry can be exported as its own PDF, titled *"The Journal of [Character Name]"* with a footer reading *"As recorded by [Player Name]"*.

!!! tip "Hidden Feature: Hero Image"
    If you've generated any [scene illustrations](../illustrations/index.md), the most recent image is automatically included at the top of your PDF as a hero image.

!!! tip "Hidden Feature: Printable Mode"
    Click **Print PDF** instead of **Export PDF** to get a **white background** version — no parchment texture, cleaner for actual printing. Same beautiful typography, just printer-friendly.

### Batch Export

!!! tip "Hidden Feature: ZIP Download"
    Click **Export All PDFs (ZIP)** to download every summary for a session in one archive:

    - Full summary saved as `session-chronicle.pdf`
    - Each POV journal saved as `{character-name}-pov.pdf`
    - All sharing the same hero image

    Also available: **Export All Printable (ZIP)** for print-friendly versions.

Next: [Text & Transcript Export →](text-export.md)
```

**Step 2: Write text export page**

`docs/guide/export/text-export.md`:

```markdown
# Text & Transcript Export

## The Written Record

Beyond PDFs, TaleKeeper offers plaintext exports for summaries and full transcript downloads.

### Summary Text Export

Click **Export Text** on any summary to download a plaintext file with:

- Campaign and session metadata header
- Session date
- Character name (for POV summaries)
- Full summary content with paragraph structure preserved

### Copy to Clipboard

Click **Copy** to copy the summary text directly to your clipboard — perfect for pasting into Discord, a blog post, or your campaign wiki.

### Transcript Export

Click **Export Transcript** to download the complete session transcript with:

- Timestamps in `[HH:MM:SS]` format
- Speaker names (character and player names when available)
- Full spoken text

Example output:
```
[00:02:15] Theron (Alex): I push open the tavern door and look around.
[00:02:23] DM (Sarah): The room falls silent. Every eye turns to you.
[00:02:31] Elara (Jordan): I cast Detect Magic, just in case.
```

Next: [Email Sharing →](email-sharing.md)
```

**Step 3: Write email sharing page**

`docs/guide/export/email-sharing.md`:

```markdown
# Email Sharing

## Sending Word by Courier

!!! tip "Hidden Feature"
    Send summaries directly to your players via email — right from TaleKeeper.

[Screenshot: Email dialog with subject and body]

### Setting Up Email

First, configure SMTP in [Settings](../settings/index.md):

| Field | Example |
|-------|---------|
| SMTP Host | `smtp.gmail.com` |
| SMTP Port | `587` |
| Username | `you@gmail.com` |
| Password | Your app password |
| Sender Address | `you@gmail.com` |

!!! info "Gmail Users"
    Use an [App Password](https://myaccount.google.com/apppasswords) — not your regular Gmail password.

### Sending a Summary

1. Click the **Email** button on any summary
2. The email dialog opens with:
    - **Subject** — pre-filled with the summary title
    - **Body** — the full summary text
    - **Copy** buttons for subject and body
3. Enter the recipient's email address
4. Click **Send**

### Manual Sharing

If you prefer to use your own email client, use the **Copy** buttons to grab the subject and body, then paste them into your email app.

Next: [Configure Settings →](../settings/index.md)
```

**Step 4: Verify build & commit**

Run: `.venv/bin/mkdocs build`

```bash
git add docs/guide/export/
git commit -m "docs: write export guide pages (PDF, text, email)"
```

---

### Task 11: Write Settings Page

**Files:**
- Create: `docs/guide/settings/index.md`

**Step 1: Write settings page**

`docs/guide/settings/index.md`:

```markdown
# Settings

## The Artificer's Workshop

The Settings page lets you configure TaleKeeper's behavior, AI providers, and integrations.

[Screenshot: Settings page overview]

### Transcription

| Setting | Description | Default |
|---------|-------------|---------|
| Whisper Model | Speech recognition model size | `medium` |
| Live Transcription | Show preview segments during recording | Off |

**Model size guide:**

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| `tiny` | ~1 min / 10 min audio | Lower | Quick tests |
| `base` | ~2 min / 10 min audio | Fair | Short sessions |
| `small` | ~4 min / 10 min audio | Good | Casual use |
| `medium` | ~8 min / 10 min audio | Very Good | **Recommended** |
| `large-v3` | ~15 min / 10 min audio | Best | Important recordings |

!!! info "Live Transcription"
    When enabled, preliminary transcript segments appear during recording. These are a preview — the final transcript after processing will be more accurate and include speaker labels.

### LLM Provider

Configure the AI that powers summaries, session naming, and scene descriptions.

| Field | Description | Default |
|-------|-------------|---------|
| Base URL | API endpoint | `http://localhost:11434/v1` |
| API Key | Authentication (optional for Ollama) | — |
| Model | Which model to use | `llama3.1:8b` |

Click **Test Connection** to verify. A green checkmark means you're connected.

!!! info "Provider Compatibility"
    Any OpenAI-compatible API works: Ollama, OpenAI, LM Studio, vLLM, Together AI, etc.

### Image Generation

Configure the AI that generates scene illustrations.

| Field | Description | Default |
|-------|-------------|---------|
| Base URL | API endpoint | `http://localhost:11434/v1` |
| API Key | Authentication (optional for Ollama) | — |
| Model | Which image model to use | `x/flux2-klein:9b` |

!!! warning "macOS Note for Ollama"
    Ollama image generation currently works only on macOS. For Linux or Windows, use a cloud provider like OpenAI (`dall-e-3`).

### Email (SMTP)

Configure email for [sharing summaries](../export/email-sharing.md).

| Field | Description | Example |
|-------|-------------|---------|
| SMTP Host | Mail server | `smtp.gmail.com` |
| SMTP Port | Server port | `587` |
| Username | Login | `you@gmail.com` |
| Password | App password | ••••••••  |
| Sender Address | From address | `you@gmail.com` |

!!! info "Password Security"
    Passwords are encrypted at rest in TaleKeeper's database. They're never stored in plaintext.

### Data Directory

Where TaleKeeper stores all recordings, transcripts, images, and the database.

- Click **Browse** to open your system's native folder picker
- Or type a path directly
- Default: `data/` in the TaleKeeper directory

!!! tip "Backup This Folder"
    Your entire TaleKeeper archive lives in this directory. Back it up to preserve your campaign history.

### Re-run Setup Wizard

Click **Run Setup Wizard** at the bottom to walk through initial configuration again.

### Environment Variables

For advanced users, TaleKeeper also respects these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TALEKEEPER_CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:5173` |
| `TALEKEEPER_SECRET` | Encryption key for stored passwords | Built-in default |
| `LLM_BASE_URL` | LLM provider URL | `http://localhost:11434/v1` |
| `LLM_API_KEY` | LLM API key | — |
| `LLM_MODEL` | LLM model name | `llama3.1:8b` |
| `IMAGE_API_KEY` | Image provider API key | — |
| `IMAGE_MODEL` | Image model name | `x/flux2-klein:9b` |

!!! note "Priority"
    Settings saved in the UI take precedence over environment variables.

Next: [Tips & Tricks →](../tips-and-tricks.md)
```

**Step 2: Verify build & commit**

Run: `.venv/bin/mkdocs build`

```bash
git add docs/guide/settings/
git commit -m "docs: write settings guide page"
```

---

### Task 12: Write Tips & Tricks Page

**Files:**
- Create: `docs/guide/tips-and-tricks.md`

**Step 1: Write tips page**

```markdown
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
```

**Step 2: Verify build & commit**

Run: `.venv/bin/mkdocs build`

```bash
git add docs/guide/tips-and-tricks.md
git commit -m "docs: write tips and tricks guide page"
```

---

### Task 13: Final Verification & Polish

**Step 1: Full build test**

Run: `.venv/bin/mkdocs build --strict`
Expected: Clean build, no warnings

**Step 2: Local preview**

Run: `.venv/bin/mkdocs serve`
Manually verify: navigation works, pages render, admonitions display, keyboard shortcut syntax renders

**Step 3: Fix any broken links or formatting issues**

**Step 4: Final commit**

```bash
git add -A docs/guide/ mkdocs.yml
git commit -m "docs: complete user guide with MkDocs Material site"
```
