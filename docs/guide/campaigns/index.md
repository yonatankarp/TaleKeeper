# Managing Campaigns

## Founding Your Company

A **campaign** is your top-level container — think of it as one continuous adventure or storyline. Each campaign holds sessions, a character roster, and shared settings.

### Creating a Campaign

![New Campaign form with name, description, language, speaker count, and first session number fields](../images/campaign-creation-form.png)

| Field | Description | Default |
|-------|-------------|---------|
| Name | Your campaign's title | — |
| Description | A brief synopsis | — |
| Language | Primary spoken language | English |
| Number of Speakers | Expected party size (1–10) | 5 |

!!! tip "Speaker Count Matters"
    The speaker count helps TaleKeeper's diarization (speaker detection) algorithm. Set it close to your actual party size for the best results — it's not a hard limit, just a hint.

### The Campaign Dashboard

![Campaign dashboard showing session count, total recorded time, and a list of sessions with status badges like COMPLETED, AUDIO, TRANSCRIPT, SUMMARY, and IMAGES](../images/campaign-dashboard.png)

Your dashboard shows:

- All sessions in chronological order
- Session count, total recorded time, and most recent session date
- Quick access to create a new session

### Editing Campaign Settings

Click on the campaign name or settings to modify:

- **Name and description** — update anytime
- **Language** — changes the default for new sessions
- **Speaker count** — adjusts diarization defaults
- **Voice Signature Confidence** — controls how strictly voice signatures are matched (0–1 range, default 0.65). Lower values are more lenient, higher values are stricter
- **Session start number** — for campaigns that didn't start at session 1

!!! tip "Hidden Feature: Session Renumbering"
    Changing the **session start number** automatically renumbers all existing sessions and updates any sessions that still have the default "Session N" name. Useful if you're importing a campaign that started as session 15 in a larger arc.

### Deleting a Campaign

Deleting a campaign permanently removes all its sessions, recordings, transcripts, summaries, and images. This cannot be undone.

Next: [Set Up Your Character Roster →](roster.md)
