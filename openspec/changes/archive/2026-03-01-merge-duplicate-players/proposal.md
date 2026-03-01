## Why

During transcription with speaker diarization, the system may detect the same real person as multiple distinct speakers — especially across sessions or when diarization clustering is imperfect. Currently there is no way to merge these duplicate speakers within a session. Users must manually reassign every individual transcript segment from one speaker to another, which is tedious and error-prone for long sessions.

## What Changes

- Add the ability to merge two speakers within a session, combining all their transcript segments under a single speaker identity
- When merging, the user picks a "target" speaker (the one to keep) and a "source" speaker (the one to absorb); all segments from the source are reassigned to the target, and the source speaker is deleted
- Optionally propagate the merge to voice signatures if both speakers had been linked to roster entries (merge embeddings or discard the source's signature)
- Expose this through both a backend API endpoint and a frontend UI action in the SpeakerPanel

## Capabilities

### New Capabilities

- `speaker-merge`: Merging two speakers within a session — selecting target/source, reassigning segments, cleaning up the source speaker record, and optionally reconciling voice signatures

### Modified Capabilities

- `speaker-diarization`: The diarization spec needs to acknowledge that post-diarization speaker merge is possible, and that the speaker list for a session may shrink after user-initiated merges

## Impact

- **Backend**: New API endpoint(s) in `src/talekeeper/routers/speakers.py`; database operations on `speakers` and `transcript_segments` tables; optional cleanup in `voice_signatures`
- **Frontend**: New merge UI in `frontend/src/components/SpeakerPanel.svelte` (merge button, target/source selection flow)
- **Database**: No schema changes required — merge operates on existing `speakers` and `transcript_segments` tables via UPDATE and DELETE
- **Voice signatures**: If both merged speakers had voice signatures linked to different roster entries, the user should decide which to keep or whether to consolidate
