## Context

Speaker diarization currently uses unsupervised agglomerative clustering on ECAPA-TDNN embeddings. With a single microphone recording multiple speakers, the clustering over-segments badly (10+ speakers detected from 2 people). The ECAPA-TDNN encoder is already loaded and produces 192-dimensional embeddings — the infrastructure for voice signatures is largely in place.

Speakers are currently scoped to sessions (`speakers.session_id`). Voice signatures need to be scoped to campaigns so they persist across sessions.

## Goals / Non-Goals

**Goals:**
- Enable extracting voice signatures from manually-labeled session audio
- Store signatures at the campaign level, linked to roster entries
- Use signatures during diarization to match speakers by similarity instead of blind clustering
- Improve cold-start clustering for sessions without signatures
- Keep the approach simple — no new ML dependencies

**Non-Goals:**
- Real-time enrollment during recording (future improvement)
- Speaker verification / authentication
- Handling more than ~10 speakers per campaign (D&D party size)
- Automatic re-enrollment after signature generation (manual trigger only)

## Decisions

### 1. Store embeddings as JSON-serialized float arrays in SQLite

Voice signatures are 192-dimensional float vectors. Store them as JSON arrays in a TEXT column on a new `voice_signatures` table.

**Why over BLOB:** JSON is human-debuggable, trivially serializable with `json.dumps`/`json.loads`, and the 192-float vector is ~2KB — no performance concern at this scale.

**Why over file-based storage:** Keeps everything in one place with the rest of the data. No file cleanup concerns.

### 2. Campaign-scoped signatures linked to roster entries

A voice signature belongs to a campaign roster entry (player + character). This naturally maps to "this is what Player X sounds like across all sessions in this campaign."

**Table: `voice_signatures`**
- `id` INTEGER PRIMARY KEY
- `campaign_id` INTEGER REFERENCES campaigns(id)
- `roster_entry_id` INTEGER REFERENCES roster_entries(id)
- `embedding` TEXT (JSON array of 192 floats)
- `source_session_id` INTEGER REFERENCES sessions(id) — which session it was extracted from
- `num_samples` INTEGER — how many audio windows contributed to this embedding
- `created_at` TEXT

One signature per roster entry. Regenerating replaces the old one.

### 3. Extract signatures by averaging embeddings from labeled segments

When the user triggers "Generate Voice Signatures" on a session:
1. Load the session WAV
2. For each speaker with a roster entry assignment (player_name + character_name match), collect all transcript segments assigned to that speaker
3. For each segment's time range, extract ECAPA-TDNN embeddings using the existing windowed approach
4. Average all embeddings for that speaker → one 192-dim vector
5. L2-normalize the averaged vector (for stable cosine similarity)
6. Store in `voice_signatures`

**Why average + normalize:** Simple, well-proven for speaker verification. Averaging smooths out per-window noise. L2-normalization ensures cosine similarity == dot product, which is fast and stable.

### 4. Signature-based diarization: nearest-neighbor matching

When signatures exist for a campaign, replace clustering with:
1. Extract windowed embeddings as before
2. For each window embedding, compute cosine similarity against all campaign signatures
3. Assign to the closest signature above a minimum similarity threshold
4. Windows below threshold are labeled "Unknown Speaker"
5. Merge adjacent same-speaker segments as before

**Threshold:** Start with cosine similarity >= 0.25 (cosine distance <= 0.75). This is lenient enough to handle mic variability while still discriminating between speakers.

### 5. Improved cold-start clustering parameters

For sessions without signatures (first session, new campaign):
- Increase `WINDOW_SIZE_SEC` from 1.5 → 3.0 (more stable embeddings)
- Increase `HOP_SIZE_SEC` from 0.75 → 1.5 (maintain 50% overlap)
- Increase `COSINE_DISTANCE_THRESHOLD` from 0.7 → 1.0 (more permissive merging)

These changes reduce over-segmentation for the unsupervised fallback path.

### 6. UI: "Generate Voice Signatures" action in speaker panel

After manually labeling speakers on a session (assigning player/character names from roster), a "Generate Voice Signatures" button appears. It calls a new API endpoint, extracts signatures, and shows confirmation with how many samples were used per speaker.

The button only appears when:
- The session has audio and transcript segments
- At least one speaker is assigned to a roster entry

## Risks / Trade-offs

**Single-session signatures may not generalize** → Mitigation: averaging over many windows from a full session provides robust embeddings. Future enhancement could merge signatures across multiple sessions.

**Single-mic recording quality limits discrimination** → Mitigation: ECAPA-TDNN is trained on diverse audio conditions (VoxCeleb). Signature matching is fundamentally more robust than unsupervised clustering for this scenario.

**"Unknown Speaker" segments if threshold is too strict** → Mitigation: Use a lenient threshold (0.25 similarity). Users can manually reassign any mismatches. Better to over-assign than over-segment.

**Stale signatures if a player's voice characteristics change** → Mitigation: Regeneration is a manual one-click action. Users regenerate from any session.
