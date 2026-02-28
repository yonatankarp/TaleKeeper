# Language Selection for Transcription

## Goal

Add the ability to select which language Whisper uses for transcription, replacing the hardcoded `language="en"`. Language is stored per-session with campaign-level defaults. Users can also override language when retranscribing.

## Decisions

- **Per-session storage** with campaign-level defaults
- **All Whisper-supported languages** (~100) via searchable dropdown
- **No auto-detect** (unreliable for non-English languages like Hebrew)
- **Retranscribe override** - language dropdown pre-filled from session, changeable

## Database Changes

### `campaigns` table
Add `language TEXT NOT NULL DEFAULT 'en'` - serves as default for new sessions.

### `sessions` table
Add `language TEXT NOT NULL DEFAULT 'en'` - the language used for transcription.

### Migration
`ALTER TABLE` statements for existing databases (SQLite `CREATE TABLE IF NOT EXISTS` won't add columns to existing tables).

## Backend Changes

### `services/transcription.py`
- `transcribe(wav_path, model_size, language)` - accept language parameter
- `transcribe_stream(wav_path, model_size, language)` - accept language parameter
- Replace hardcoded `language="en"` with the parameter

### `routers/campaigns.py`
- Accept `language` in create/update

### `routers/sessions.py`
- `SessionCreate` gains `language: str | None` field
- On create: if language not provided, read campaign's default language
- `SessionUpdate` gains `language: str | None` field
- Session response includes `language` field

### `routers/transcripts.py`
- `RetranscribeRequest` gains `language: str | None` field
- Use request language if provided, else session's stored language
- Pass language to `transcribe()`

### `routers/recording.py`
- Read session's language from DB at WebSocket connect
- Pass language to `transcribe()` in `_run_transcription_on_chunk()`

## Frontend Changes

### New: `LanguageSelect.svelte`
Searchable dropdown component containing all Whisper-supported languages. Text input filters the list. Displays language name with code (e.g., "English (en)").

### Campaign create/edit
Add `<LanguageSelect>` to campaign form. Default: English.

### Session create
Pre-fill language from campaign default. Allow override via `<LanguageSelect>`.

### `TranscriptView.svelte`
Add language selector next to the Retranscribe button. Pre-filled with session's language. Passed to the retranscribe API call.

### `SessionDetail.svelte`
Pass session language to child components.

## Language List

All languages supported by faster-whisper / OpenAI Whisper, stored as ISO 639-1 codes (e.g., "en", "he", "fr"). The full list is defined once in a shared constants file on the frontend.
