## Context

TaleKeeper's diarization uses AgglomerativeClustering to group speaker embeddings. The clustering has two modes: threshold-based (automatic speaker count) and fixed-count (`num_speakers`). Currently only threshold-based mode is used, which is unreliable — the threshold either over-segments (10+ phantom speakers) or under-segments (all merged into one). The `_cluster_embeddings` function already accepts a `num_speakers` parameter but no caller provides it.

Campaigns are the natural home for this setting since table size is consistent across sessions.

## Goals / Non-Goals

**Goals:**
- Let the DM specify how many speakers to expect per campaign
- Pass that count through to `_cluster_embeddings` during final diarization
- Add the field to campaign create/edit forms with a sensible default
- Migrate existing databases with a default value

**Non-Goals:**
- Persisting a per-session speaker count override in the database (the override is transient and passed at call time)
- Changing how real-time/chunk diarization works (only final pass uses this)
- Removing or changing the threshold-based fallback (it remains when `num_speakers` is None)

## Decisions

### D1: Store `num_speakers` on the campaigns table with default 5

**Rationale:** D&D tables typically have 4-6 players plus a DM. A default of 5 covers most groups and is easily changed. Storing on campaigns (not sessions) avoids repetitive configuration since party size is stable across sessions.

**Alternatives considered:**
- Per-session setting: More flexible but tedious to set every session. Can be added later if needed.
- No default / required field: Worse UX for campaign creation — most users won't know what to set immediately.

### D2: Fetch `num_speakers` inside `run_final_diarization` from the campaign

**Rationale:** `run_final_diarization` already receives `session_id` and can look up the campaign. This avoids changing the signature of the three callers (`recording.py` x2, `transcripts.py` x1). The value is fetched only during the final pass, not during real-time chunk diarization.

**Alternatives considered:**
- Pass through all callers: More explicit but changes 3 call sites for no benefit since the value comes from the DB anyway.

### D3: Add column via `ensure_tables` with ALTER TABLE fallback

**Rationale:** TaleKeeper uses SQLite with `CREATE TABLE IF NOT EXISTS` in `ensure_tables()`. For existing databases, add an `ALTER TABLE ADD COLUMN` with a try/except to handle the case where the column already exists. This matches the project's existing migration pattern (no formal migration framework).

### D4: Validate num_speakers as integer between 1 and 10

**Rationale:** Fewer than 1 speaker is meaningless. More than 10 is unrealistic for a tabletop game and would degrade clustering quality. The frontend uses a number input with min/max constraints; the backend validates via Pydantic.

### D5: Session-level override via recording controls and retranscribe bar

**Rationale:** While `num_speakers` is stored on the campaign, individual sessions may differ (e.g., a player is absent, a guest joins). The recording controls and retranscribe bar show the campaign's `num_speakers` as an editable default. The override value is passed directly to `run_final_diarization` without changing the campaign setting.

**Alternatives considered:**
- Storing override on the session record: Adds schema complexity and a second source of truth. A transient override keeps things simple and avoids stale values.

## Risks / Trade-offs

- **[Existing sessions get default 5]** → Acceptable since re-diarization is manual. DMs can update their campaign's speaker count before re-running diarization.
- **[Override is transient]** → The per-session override is not persisted. If the user forgets to set it again on retranscribe, the campaign default is used, which is the expected behavior.
