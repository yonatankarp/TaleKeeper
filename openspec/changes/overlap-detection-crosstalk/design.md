## Context

The diarization pipeline in `services/diarization.py` runs: VAD → speaker change detection → embedding extraction → spectral clustering → segment assembly. After clustering, every subsegment gets a hard speaker label. There is no mechanism to express uncertainty — a subsegment where two players are speaking simultaneously (one near the mic, one far) gets assigned to whichever player's voice dominates, silently corrupting that content in summaries.

At the clustering stage we already have:
- `embeddings`: (N, 256) float32 array of all subsegment WeSpeaker embeddings
- `labels`: cluster assignment per embedding
- Centroids are computable trivially from these two

The detection can therefore be done entirely on already-computed data at zero extra model cost.

The two diarization entry points (`diarize` and `diarize_with_signatures`) share the same clustering step but diverge for signature matching. Overlap detection must be inserted in both paths, at the same point: after clustering, before `_build_segments_from_labels`.

## Goals / Non-Goals

**Goals:**
- Detect subsegments whose embeddings are geometrically ambiguous between two or more speaker clusters
- Label those subsegments `[crosstalk]` instead of assigning them to a single speaker
- Persist `is_overlap` on `transcript_segments` so the frontend can render them distinctly
- Exclude overlap time from per-speaker totals in the speaker panel

**Non-Goals:**
- Recovering or separating the content of overlapping speech (that is speech-source-separation)
- Detecting overlaps during live recording — this runs post-session only
- Changing the overlap threshold per-campaign (not worth the UI complexity at this stage)
- Detecting overlaps between more than two simultaneous speakers (addressed implicitly by the same algorithm)

## Decisions

### 1. Detection method: cosine similarity ratio on cluster centroids

For each embedding, compute cosine similarity to all cluster centroids. If `sim_to_second_best / sim_to_best >= OVERLAP_RATIO_THRESHOLD` (default 0.85), the embedding is ambiguous and the subsegment is marked as overlap.

**Why:** We already have the embeddings and can trivially compute centroids from `labels`. The ratio test is parameter-free except for one threshold, is interpretable, and adds negligible compute (pure numpy matmul). No extra model, no extra pass over the audio.

**Alternative considered: Energy-based detection.** Compare RMS energy of the window against a per-speaker baseline. Rejected — energy varies enormously with mic distance (the core problem we're solving), making a reliable threshold impossible without per-speaker calibration.

**Alternative considered: A dedicated overlap detection model** (e.g., pyannote's overlap segmentation model). Rejected — pyannote's MPS backend is broken on Apple Silicon and CPU inference is prohibitively slow (documented reason pyannote was removed from the project).

### 2. Represent overlap as a special label `[crosstalk]`, not a new field on `SpeakerSegment`

`SpeakerSegment` stays unchanged (`speaker_label`, `start_time`, `end_time`). Overlap subsegments get `speaker_label = "[crosstalk]"`. The `is_overlap` boolean on `transcript_segments` is derived from this label during DB writes.

**Why:** `SpeakerSegment` is the contract between diarization and all consumers (routers, alignment, merge). Changing it would require updates across 4 routers and the alignment function. A special label requires zero structural changes — consumers that don't understand `[crosstalk]` degrade gracefully (the segment simply has no matched speaker).

**Alternative considered: Add `is_overlap: bool` field to `SpeakerSegment`.** Rejected — higher blast radius, requires every consumer to handle the new field explicitly, and the label approach is equivalent.

### 3. Insert overlap detection in both `diarize` and `diarize_with_signatures` via shared helper

New private function `_flag_overlap_subsegments(embeddings, labels, threshold) -> np.ndarray` returns a boolean mask of the same length as `labels`. Both `diarize` and `diarize_with_signatures` call it after clustering, before building segments.

**Why:** Both paths do their own clustering and both produce the same `(embeddings, labels)` shape. A shared helper avoids duplicating the detection logic.

**Alternative considered: Only flag overlaps in `diarize_with_signatures`** (the signed-in path). Rejected — the unsigned path (`diarize`) is used when no voice signatures exist, and overlaps are equally harmful there.

### 4. Overlap threshold as a module-level constant, not a campaign setting

`OVERLAP_RATIO_THRESHOLD = 0.85` defined alongside the other diarization constants.

**Why:** A campaign-level setting requires a DB column, a UI control, migration, and fetch logic — significant overhead for a single float. The threshold has a natural interpretation (how similar must the second-best cluster be to the best to call it ambiguous), and 0.85 is a reasonable starting point across all use cases. Can be promoted to a campaign setting later based on user feedback.

**Alternative considered: Campaign-level setting from the start.** Rejected as premature — we don't have enough data yet to know if per-campaign tuning is needed.

### 5. DB migration: additive `is_overlap` column with DEFAULT 0

```sql
ALTER TABLE transcript_segments ADD COLUMN is_overlap INTEGER NOT NULL DEFAULT 0;
```

Existing rows default to 0 (not overlap). The migration runs in `db/connection.py` alongside existing schema migrations.

**Why:** SQLite `ALTER TABLE ADD COLUMN` with a constant default is the only safe additive migration available. No backfill needed — old sessions have no overlap data, which is correct (they were processed without this feature).

**Alternative considered: Separate `overlap_segments` table.** Rejected — it fragments the transcript_segments query surface and complicates every query that needs to know whether a segment is overlap.

## Risks / Trade-offs

**[False positives on short bursts]** Short VAD segments from players who rarely speak may have sparse, noisy embeddings that land close to multiple centroids even during solo speech. → Mitigate by only flagging embeddings where the segment duration exceeds `MIN_SEGMENT_DURATION` (already 0.4s). Can raise the threshold if false positive rate is too high in practice.

**[Sessions with few speakers produce fewer overlaps to detect]** With only 2 speakers, the embedding space is well-separated and the ratio test rarely fires even for genuine overlap. → Acceptable — two-speaker sessions have less severe overlap attribution problems anyway.

**[`[crosstalk]` label must not match any roster name]** If a player is literally named "[crosstalk]", the alignment logic will incorrectly mark their segments as overlap. → Document this constraint in code. Extremely unlikely in practice.

**[Threshold 0.85 is unvalidated]** We don't have ground-truth overlap annotations to tune this. → Start at 0.85, evaluate on the 30-minute sample session. It's a single constant that can be adjusted without schema or API changes.

## Migration Plan

1. Add `is_overlap` column migration to `db/connection.py`
2. Implement `_flag_overlap_subsegments()` and wire into both diarize paths
3. Update `run_final_diarization()` to write `is_overlap` when inserting/updating `transcript_segments`
4. Update `align_speakers_with_transcript()` to pass through `[crosstalk]` label without trying to match it to a speaker
5. Frontend: render `[crosstalk]` segments as muted blocks; exclude from speaker panel totals
6. Existing sessions: `is_overlap = 0` for all rows (no re-diarization needed, no backfill)
