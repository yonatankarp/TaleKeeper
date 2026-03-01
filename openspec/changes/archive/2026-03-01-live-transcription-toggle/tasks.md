## 1. Global setting (using existing settings table)

- [x] 1.1 ~~Add `live_transcription` column to campaigns~~ → Replaced with global setting in `settings` key-value table (no schema/migration changes needed)

## 2. Backend: Gate incremental transcription

- [x] 2.1 In `recording_ws` in `src/talekeeper/routers/recording.py`, read the `live_transcription` setting from the `settings` table at WS connection time
- [x] 2.2 Wrap the `chunk_count % 10 == 0` incremental transcription block with a check on the `live_transcription` flag — skip `_do_transcribe` when disabled

## 3. Frontend: Settings page toggle

- [x] 3.1 Add `live_transcription` default to settings load in `frontend/src/routes/SettingsPage.svelte`
- [x] 3.2 Add checkbox toggle with description to the Transcription section of the Settings page

## 4. Frontend: Preview banner in TranscriptView

- [x] 4.1 Update the processing banner in `frontend/src/components/TranscriptView.svelte`: when `status` is `audio_ready` or `transcribing` and `segments.length > 0`, show "Segments below are a preview from live transcription. Full-quality transcription is in progress..."
- [x] 4.2 When `status` is `audio_ready` or `transcribing` and `segments.length === 0`, keep the existing message "Processing audio — transcribing and identifying speakers..."
