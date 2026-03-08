## Why

Whisper produces transcript segments that can be 5–30 seconds long. A D&D session has rapid back-and-forth where multiple players speak within one Whisper segment. The current alignment function (`align_speakers_with_transcript`) assigns one speaker label to the entire transcript segment — whichever diarization speaker has the most overlap time. The minority speakers in that window are silently attributed to whoever spoke longest, producing passages like "Unfortunately my backstory doesn't work... What did I do in the meantime? That's the part where I have a hole to fill now..." all labelled as one person even though three players are talking.

Diarization already correctly finds the speaker boundaries. The problem is entirely in the alignment layer.

## What Changes

- Before alignment, split each transcript segment at diarization speaker-change boundaries that fall within its time window
- Text is split proportionally by word count (relative to time duration of each sub-segment) — an approximation until word-level timestamps are available
- The first sub-segment keeps the original DB row ID (UPDATE); additional sub-segments are INSERTed as new rows
- `align_speakers_with_transcript` runs unchanged on the expanded list — each sub-segment now overlaps only one diarization speaker

## Capabilities

### New Capabilities
- `transcript-diarization-split`: Pre-alignment splitting of transcript segments at diarization speaker boundaries, with proportional text distribution.

### Modified Capabilities
- `speaker-diarization`: `run_final_diarization` gains a pre-alignment split step and must handle INSERT (in addition to UPDATE) when writing aligned segments back to the DB.

## Impact

- **Database**: No schema changes. Existing transcript_segments rows may be split into multiple rows on re-diarization (one UPDATE + N INSERTs per split segment).
- **Backend**: `diarization.py` — new `_split_transcript_segments()` function. `run_final_diarization()` calls it before alignment and handles INSERT for new sub-segments.
- **Frontend**: No changes — sub-segments look identical to regular segments.
- **No new dependencies.**
