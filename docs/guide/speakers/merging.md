# Merging Speakers

## Joining Forces

!!! tip "Hidden Feature"
    Sometimes diarization creates two entries for the same person (e.g., "Player 1" and "Player 3" are both the DM). **Speaker merging** combines them into one.

### How to Merge

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
