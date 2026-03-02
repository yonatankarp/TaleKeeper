## Context

Speaker diarization uses `AgglomerativeClustering` from scikit-learn with ECAPA-TDNN embeddings. The clustering function (`_cluster_embeddings`) already supports two modes: threshold-based (automatic speaker count) and fixed-count (`n_clusters=num_speakers`). Currently only threshold-based is used in the main pipeline, and tuning it has proven unreliable — too low creates phantom speakers, too high merges everyone.

The campaign table stores per-campaign defaults (like `language`) that flow into sessions. `num_speakers` follows this same pattern.

## Goals / Non-Goals

**Goals:**
- Give the user explicit control over expected speaker count per campaign
- Pass this value to the clustering algorithm so it produces exactly N speakers
- Keep the change minimal — no new callers need modification

**Non-Goals:**
- Per-session speaker count override (campaign-level is sufficient for now)
- Changing the voice-signature-based diarization path (signatures don't cluster)
- Removing the distance threshold fallback entirely (kept for edge cases)

## Decisions

### 1. Campaign-level field, not session-level

Store `num_speakers` on the `campaigns` table only. The diarization function (`run_final_diarization`) already queries the campaign for voice signatures — it can fetch `num_speakers` in the same query. This means zero changes to the three callers of `run_final_diarization`.

**Why not session-level:** A D&D campaign typically has the same players each session. Adding per-session overrides adds complexity with minimal benefit. Can be added later if needed.

### 2. Default value of 5

`INTEGER NOT NULL DEFAULT 5`. A typical D&D table has 1 DM + 4 players. 5 is a safe default. Validation range: 2-10 (minimum 2 = DM + 1 player, maximum 10 = DM + 9 players).

**Why not NULL:** The user asked for this to be required. A NULL value would fall back to threshold-based clustering, which is exactly the behavior we're replacing.

### 3. Fetch num_speakers inside run_final_diarization

The function already opens a DB connection and queries `sessions` → `campaigns` for voice signatures. Adding `num_speakers` to the campaign query is trivial. This avoids threading a new parameter through all three call sites (recording.py WebSocket close, recording.py process-audio, transcripts.py retranscribe).

### 4. Only affects the clustering fallback path

When voice signatures exist, diarization uses nearest-neighbor matching (no clustering). `num_speakers` only applies to the else branch where `diarize()` is called. The `diarize()` function signature gains an optional `num_speakers` parameter and forwards it to `_run_pipeline` → `_cluster_embeddings`.

## Risks / Trade-offs

**Fixed count may not match actual speakers in a session** → The user can edit the campaign setting before re-processing. In practice, D&D groups are stable. Future enhancement could add per-session override.

**Existing campaigns get default of 5** → Migration uses `DEFAULT 5`. If a campaign typically has 7 players, the user needs to update it once. This is acceptable since the feature is new.
