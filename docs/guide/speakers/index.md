# Speaker Assignment

## Naming the Voices

After transcription, TaleKeeper's diarization identifies distinct speakers and labels them as "Player 1", "Player 2", etc. Your job is to assign real names.

![Chronicle tab showing the transcript with color-coded speaker labels, timestamps, audio player, and Retranscribe / Re-diarize buttons](../images/speaker-panel.png)

### Assigning Names

For each detected speaker:

1. Set the **Player Name** (the real person)
2. Set the **Character Name** (their in-game persona)

!!! tip "Roster Suggestions"
    If you've set up your [Character Roster](../campaigns/roster.md), a dropdown suggests names from your campaign's active roster members. No need to type — just select.

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
