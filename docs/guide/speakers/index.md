# Speaker Assignment

## Naming the Voices

After transcription, TaleKeeper identifies distinct speakers and labels them as "Player 1", "Player 2", etc. Your job is to assign real names.

!!! info "Automatic Recognition"
    If you've set up [voice signatures](voice-signatures.md) for your roster, TaleKeeper may have already identified some or all speakers automatically. You'll see their character names instead of generic labels.

![Chronicle tab showing the transcript with color-coded speaker labels, VS badges, timestamps, audio player, Edit All, Generate Voice Signatures, Retranscribe, and Re-diarize buttons](../images/speaker-panel.png)

### Assigning Names

For each detected speaker:

1. Set the **Player Name** (the real person)
2. Set the **Character Name** (their in-game persona)

!!! tip "Roster Suggestions"
    If you've set up your [Character Roster](../campaigns/roster.md), quick-fill buttons suggest names from your active roster. Click one to instantly assign both the player and character name.

### Edit All Speakers at Once

Instead of editing speakers one by one, click **Edit All** in the speaker panel header. This opens every speaker for editing at once, with roster suggestion buttons for quick assignment. Much faster when you need to label a full party.

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
    - Background noise made it hard to tell speakers apart

### Generating Voice Signatures

Once you've labeled all speakers and matched them to roster entries, you can teach TaleKeeper to recognize their voices in future sessions:

1. Expand the **Speakers** panel
2. Click the green **Generate Voice Signatures** button
3. TaleKeeper analyzes each speaker's audio and builds a voice profile

Speakers with stored voice signatures show a green **VS** badge. See [Voice Signatures](voice-signatures.md) for the full guide.

Next: [Merge Duplicate Speakers →](merging.md)
