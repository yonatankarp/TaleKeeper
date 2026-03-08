## Context

`run_final_diarization` calls `align_speakers_with_transcript(segments, transcript_segs)` where:
- `segments`: list of `SpeakerSegment` objects from the diarization pipeline (fine-grained, sub-second boundaries)
- `transcript_segs`: list of dicts from `SELECT id, start_time, end_time FROM transcript_segments`

`align_speakers_with_transcript` picks the highest-overlap diarization speaker per transcript segment. When a 15s Whisper segment spans 4 speakers, the one with the most seconds wins and the others are erased.

The fix is a pre-alignment pass: **split transcript segments at diarization boundaries before alignment runs**. After splitting, each sub-segment overlaps at most one diarization speaker, so alignment assigns the correct label.

## Goals / Non-Goals

**Goals:**
- Split transcript segments at speaker-change boundaries when a diarization change falls within the segment's time window
- Distribute text proportionally by word count across sub-segments (time-proportional approximation)
- No DB schema changes
- No frontend changes
- Both diarize paths (`diarize` + `diarize_with_signatures`) benefit automatically since they both call `run_final_diarization`

**Non-Goals:**
- Word-level timestamp accuracy (deferred to a future word-timestamps feature)
- Splitting at `[crosstalk]` boundaries specifically — crosstalk segments are handled by existing `is_overlap` logic and the split works correctly with them
- Live recording — post-session only

## Decisions

### 1. Split before alignment, not inside alignment

`align_speakers_with_transcript` is a pure function that maps a transcript segment to a speaker. Splitting inside it would require it to return a variable-length list of segments per input segment, breaking the current one-in / one-out contract.

Splitting before alignment keeps the function unchanged and makes the logic explicit: the transcript list is expanded, then alignment runs as normal.

**Alternative considered: modify `align_speakers_with_transcript` to return multiple segments per input.** Rejected — changes the contract, harder to test, and couples two concerns (splitting + alignment).

### 2. Text splitting by word proportion, not character proportion

Words are the natural unit of readable text. Character proportion would split mid-word; word proportion doesn't.

Formula: for sub-segment with duration `d` out of total `D`, take `round(d/D * len(words))` words. Any rounding remainder goes to the last sub-segment.

**Alternative considered: no text splitting — first sub-segment gets all text, others get empty string.** Rejected — empty sub-segments are confusing in the UI and harder to use for summaries.

**Alternative considered: all sub-segments get the full text (duplicated).** Rejected — produces duplicate text in summaries.

### 3. First sub-segment keeps original DB row ID; additional sub-segments are INSERTed

Re-using the original ID for the first sub-segment means:
- One UPDATE per split segment (same as unchanged segments) for the first sub
- N-1 INSERTs for the remaining subs
- No DELETE required

**Alternative considered: DELETE original + INSERT all.** Rejected — creates new IDs unnecessarily and is two operations instead of one for the first sub-segment.

### 4. Split only on speaker-change boundaries, not on `[crosstalk]` boundaries

`[crosstalk]` diarization segments are already handled by `align_speakers_with_transcript` (they set `is_overlap=1`). Including them in splitting is fine — the split function is speaker-label-agnostic. A transcript segment that overlaps both `SPEAKER_00` and `[crosstalk]` will be split, and each sub-segment will be handled correctly by alignment.

### 5. Minimum sub-segment duration guard

Sub-segments shorter than `MIN_SEGMENT_DURATION` (0.4s) are merged with the adjacent sub-segment to avoid microscopic text fragments. This matches the diarization pipeline's own minimum.

## Implementation

### New function: `_split_transcript_segments`

```python
def _split_transcript_segments(
    transcript_segs: list[dict],
    speaker_segs: list[SpeakerSegment],
) -> list[dict]:
```

For each transcript segment `t`:
1. Collect all speaker segment boundaries that fall strictly inside `(t.start_time, t.end_time)` — these are split points
2. If no split points → yield `t` unchanged
3. Otherwise:
   - Build sub-intervals: `[t.start, split1, split2, ..., t.end]`
   - Merge sub-intervals shorter than `MIN_SEGMENT_DURATION` into the adjacent one
   - Split `t["text"]` proportionally by word count
   - First sub-segment: copy `t` with updated `start_time`/`end_time`/`text` (same `id`)
   - Additional sub-segments: new dicts with `id=None`, same `session_id`, new `start_time`/`end_time`/`text`

### Changes to `run_final_diarization`

Both the signed and unsigned branches call the same pattern:

```python
# BEFORE alignment:
transcript_segs = _split_transcript_segments(transcript_segs, segments)

# alignment unchanged:
aligned = align_speakers_with_transcript(segments, transcript_segs)

# AFTER alignment, DB writes:
for seg in aligned:
    if seg.get("id") is not None:
        # UPDATE existing row (unchanged or first sub-segment)
        await db.execute("UPDATE transcript_segments SET ... WHERE id = ?", (..., seg["id"]))
    else:
        # INSERT new row (additional sub-segments from split)
        await db.execute("INSERT INTO transcript_segments (...) VALUES (...)", (...))
```

The existing UPDATE path is otherwise identical to what it is today.

## Risks / Trade-offs

**[Text attribution is approximate]** Word-proportional splitting will misattribute some words at boundaries — the last words assigned to speaker A may actually belong to speaker B. This is unavoidable without word-level timestamps and is still dramatically better than attributing the whole passage to one speaker.

**[Very short sub-segments may produce single-word fragments]** A 0.5s diarization segment inside a 15s transcript segment would get ~3% of the words — possibly just one or two words. The minimum duration guard reduces but does not eliminate this.

**[Re-diarization on sessions with many long Whisper segments will produce more DB rows]** Each long segment may become 2–5 rows. At D&D session scale (hundreds of segments), this is negligible.

**[`session_id` must be propagated to new rows]** The transcript_segs query currently only fetches `id, start_time, end_time`. It must also fetch `session_id` (and any other NOT NULL columns without defaults) so INSERTs can populate them.
