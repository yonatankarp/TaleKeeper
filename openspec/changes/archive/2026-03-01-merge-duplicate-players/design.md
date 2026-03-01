## Context

After speaker diarization, a session may contain duplicate speakers representing the same real person. This happens when the clustering algorithm splits one voice into multiple labels, or when signature-based matching partially fails. Today the only workaround is manually reassigning every transcript segment one-by-one (or via bulk reassign), which is slow and doesn't clean up the orphaned speaker record.

The existing speaker infrastructure already supports:
- Listing speakers per session (`GET /api/sessions/{id}/speakers`)
- Updating speaker identity (`PUT /api/speakers/{id}`)
- Reassigning individual or bulk segments (`PUT /api/transcript-segments/{id}/speaker`, `PUT /api/sessions/{id}/reassign-segments`)
- Voice signature generation tied to roster entries

The merge operation is a natural extension: bulk-reassign all segments from source to target, then delete the source speaker.

## Goals / Non-Goals

**Goals:**
- Single API call to merge two speakers within a session (reassign all segments + delete source)
- Frontend merge flow in SpeakerPanel with clear target/source selection
- Handle the case where the source speaker has a voice signature linked to a roster entry
- Atomic operation — either the full merge succeeds or nothing changes

**Non-Goals:**
- Cross-session speaker merging (merging speakers across different sessions)
- Automatic duplicate detection / suggested merges (could be a future enhancement)
- Merging roster entries themselves — this operates at the session speaker level only
- Batch merge of 3+ speakers in a single operation (users can merge pairwise)

## Decisions

### 1. Single endpoint: `POST /api/sessions/{session_id}/merge-speakers`

**Choice:** One dedicated merge endpoint rather than composing existing reassign + delete calls from the frontend.

**Rationale:** Merge must be atomic — if segment reassignment succeeds but speaker deletion fails, the session is in an inconsistent state. A single endpoint wraps everything in one database transaction. It also simplifies the frontend to a single API call.

**Alternatives considered:**
- *Frontend orchestration (call reassign-segments then delete speaker)*: No atomicity guarantee; more complex frontend error handling; extra round-trips.

### 2. Request body: `{ source_speaker_id, target_speaker_id }`

**Choice:** The caller explicitly picks which speaker to keep (target) and which to absorb (source).

**Rationale:** This is unambiguous. The target keeps its identity (player_name, character_name, diarization_label). The source's segments move to the target, then the source is deleted.

**Alternatives considered:**
- *Auto-select target based on segment count*: Surprising behavior; user should be in control.

### 3. Voice signature handling: delete source's signature

**Choice:** If the source speaker is linked to a roster entry that has a voice signature, delete that voice signature during the merge. The target's voice signature (if any) is preserved as-is.

**Rationale:** After merge, the source speaker no longer exists, so its voice signature is stale. The user can regenerate voice signatures after merge if they want updated embeddings. This keeps the merge operation simple and predictable. No roster entry changes are made — only the voice signature row is cleaned up.

**Alternatives considered:**
- *Merge embeddings (average them)*: Complex, and the averaged embedding may be worse than either individual one. Better to let the user regenerate.
- *Prompt user to choose*: Adds UI complexity for a rare edge case. Simpler to always delete source's signature and let users regenerate.
- *Leave orphaned signatures*: Would cause confusion — a voice signature pointing to a roster entry whose speaker no longer exists in the session.

### 4. Frontend flow: merge button per speaker in batch edit mode

**Choice:** Add a "Merge into..." action per speaker row in the SpeakerPanel's batch edit mode. Clicking it opens a dropdown/selector of other speakers in the session, confirming merges the two.

**Rationale:** Batch edit mode already shows all speakers with edit controls — it's the natural place for merge. The flow is: click merge on the source speaker → select target → confirm → done.

**Alternatives considered:**
- *Drag-and-drop speakers*: Higher implementation cost, less accessible, unfamiliar pattern for this context.
- *Separate merge dialog/page*: Unnecessary navigation; the speaker list is already visible in batch edit mode.

### 5. Validation rules

- Source and target must be different speakers
- Both must belong to the same session
- Session must match the URL parameter
- Source speaker must exist (not already merged/deleted)

## Risks / Trade-offs

- **Irreversible operation** → Show a confirmation dialog before merging. The dialog should clearly state which speaker will be removed and how many segments will be reassigned.
- **Voice signature loss** → Clearly communicate in the confirmation dialog that the source speaker's voice signature (if any) will be deleted. Suggest regenerating signatures after merge.
- **Summary regeneration** → After merge, existing session summaries may reference the old speaker name. This is acceptable — the user can regenerate the summary. Not worth auto-triggering.
