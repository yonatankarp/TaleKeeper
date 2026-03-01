## Context

Live transcription runs during recording via `_run_transcription_on_chunk` in the WS handler (`recording.py`). Every 10 audio chunks, it concatenates all chunks, converts to WAV, and transcribes the new portion. These incremental results are low-quality compared to the full `transcribe_chunked` pipeline that runs after recording stops (overlapping chunks with deduplication).

After the recent auto-retranscribe change, recording stop already triggers the full-quality pipeline (`process-audio` endpoint). The incremental segments are cleared and replaced. Users see segments appear during recording, then disappear and get replaced — which is confusing.

Campaign settings are stored as columns on the `campaigns` table. The existing pattern: `language` (text), `num_speakers` (integer). Both are exposed in create/edit forms on `CampaignList.svelte` and passed through to backend via Pydantic models in `campaigns.py`.

## Goals / Non-Goals

**Goals:**
- Make live transcription opt-in per campaign, disabled by default
- When live transcription is off, no segments appear during recording (cleaner UX)
- When live transcription is on and audio is processing post-recording, clearly label existing segments as "preview"

**Non-Goals:**
- Improving the quality of incremental transcription itself
- Adding a global (app-wide) setting — campaign-level is sufficient
- Changing the post-recording processing pipeline

## Decisions

### Campaign-level setting (not global)
Different campaigns may have different preferences. The existing pattern stores settings as campaign columns (`language`, `num_speakers`), so `live_transcription` follows the same pattern. A global setting would require checking both levels and adds complexity for no benefit.

### Boolean column with `DEFAULT 0` (disabled)
Keeps the schema simple. SQLite stores booleans as integers. The migration `ALTER TABLE campaigns ADD COLUMN live_transcription INTEGER NOT NULL DEFAULT 0` is non-breaking — existing campaigns get the feature disabled, which is the desired default.

### Gate at the WS handler level
The toggle point is the `if chunk_count % 10 == 0 and not transcription_in_progress` condition in `recording_ws`. Reading the campaign's `live_transcription` flag once at WS connection time (when the session is already being looked up) avoids repeated DB reads. Simply skip the `asyncio.create_task(_do_transcribe(...))` call when the flag is off.

### Preview banner in TranscriptView
When `status` is `audio_ready` or `transcribing` and segments exist (from live transcription), show a distinct banner: "Segments below are a preview. Full-quality transcription is in progress...". When no segments exist (live transcription was off), keep the current message. This reuses the existing `processing-banner` CSS class and the `status` prop already wired through from `SessionDetail`.

## Risks / Trade-offs

- **Users upgrading with live transcription expectations**: Existing users who relied on seeing live segments will now see nothing during recording by default. This is intentional per user feedback — the "Waiting for speech..." empty state is less confusing than low-quality disappearing segments. Users can re-enable per campaign.
- **Campaign setting not surfaced prominently**: The toggle is in the campaign create/edit form alongside language and speaker count. It won't be obvious to new users that the option exists. Acceptable for now — it's an advanced feature.
