# Language Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-session language selection for Whisper transcription, with campaign-level defaults and retranscribe override.

**Architecture:** Add `language` column to both `campaigns` and `sessions` tables. Sessions inherit language from their campaign on creation. The transcription service accepts language as a parameter instead of hardcoding `"en"`. Frontend gets a searchable `LanguageSelect` component used in campaign forms, session creation, and retranscribe.

**Tech Stack:** Python/FastAPI backend, Svelte 5 (runes) frontend, SQLite via aiosqlite, faster-whisper

---

### Task 1: Database schema migration — add language columns

**Files:**
- Modify: `src/talekeeper/db/connection.py`

**Step 1: Add language columns to schema and migration**

In `src/talekeeper/db/connection.py`, add `language TEXT NOT NULL DEFAULT 'en'` to both the `campaigns` and `sessions` CREATE TABLE statements in `_SCHEMA`. Then add migration logic in `_apply_schema` to ALTER TABLE for existing databases (since `CREATE TABLE IF NOT EXISTS` won't add new columns).

Update `_SCHEMA` — add `language` column to campaigns table:

```python
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    language TEXT NOT NULL DEFAULT 'en',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

And to sessions table:

```python
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    language TEXT NOT NULL DEFAULT 'en',
    audio_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Update `_apply_schema` to add migration after `db.executescript(_SCHEMA)`:

```python
async def _apply_schema(db: aiosqlite.Connection) -> None:
    """Create all tables if they don't exist."""
    await db.executescript(_SCHEMA)
    # Migrations for existing databases
    await _migrate_add_language_columns(db)


async def _migrate_add_language_columns(db: aiosqlite.Connection) -> None:
    """Add language column to campaigns and sessions if missing."""
    for table in ("campaigns", "sessions"):
        cols = await db.execute_fetchall(f"PRAGMA table_info({table})")
        col_names = [c["name"] for c in cols]
        if "language" not in col_names:
            await db.execute(
                f"ALTER TABLE {table} ADD COLUMN language TEXT NOT NULL DEFAULT 'en'"
            )
```

**Step 2: Verify migration works**

Run: `cd /Users/yonatankarp-rudin/Projects/TaleKeeper && python -c "import asyncio; from talekeeper.db import init_db; asyncio.run(init_db()); print('OK')"`
Expected: `OK` (no errors)

**Step 3: Commit**

```bash
git add src/talekeeper/db/connection.py
git commit -m "feat: add language column to campaigns and sessions tables"
```

---

### Task 2: Transcription service — accept language parameter

**Files:**
- Modify: `src/talekeeper/services/transcription.py`

**Step 1: Add language parameter to transcribe()**

Replace the `transcribe` function signature and body. Change `language="en"` to use the parameter:

```python
def transcribe(wav_path: Path, model_size: str = "medium", language: str = "en") -> list[TranscriptSegment]:
    """Transcribe a WAV file and return segments with timestamps."""
    model = get_model(model_size)
    segments, _ = model.transcribe(
        str(wav_path),
        language=language,
        beam_size=5,
        vad_filter=True,
    )

    results = []
    for seg in segments:
        results.append(
            TranscriptSegment(
                text=seg.text.strip(),
                start_time=seg.start,
                end_time=seg.end,
            )
        )
    return results
```

**Step 2: Add language parameter to transcribe_stream()**

```python
def transcribe_stream(wav_path: Path, model_size: str = "medium", language: str = "en") -> Iterator[TranscriptSegment]:
    """Stream transcription segments as they are produced."""
    model = get_model(model_size)
    segments, _ = model.transcribe(
        str(wav_path),
        language=language,
        beam_size=5,
        vad_filter=True,
    )

    for seg in segments:
        yield TranscriptSegment(
            text=seg.text.strip(),
            start_time=seg.start,
            end_time=seg.end,
        )
```

**Step 3: Commit**

```bash
git add src/talekeeper/services/transcription.py
git commit -m "feat: add language parameter to transcription functions"
```

---

### Task 3: Campaign API — accept language field

**Files:**
- Modify: `src/talekeeper/routers/campaigns.py`

**Step 1: Add language to Pydantic models**

Update `CampaignCreate`:

```python
class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    language: str = "en"
```

Update `CampaignUpdate`:

```python
class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    language: str | None = None
```

**Step 2: Pass language in create_campaign INSERT**

Update the INSERT in `create_campaign`:

```python
cursor = await db.execute(
    "INSERT INTO campaigns (name, description, language) VALUES (?, ?, ?)",
    (body.name, body.description, body.language),
)
```

**Step 3: Handle language in update_campaign**

Add language handling in `update_campaign` alongside the existing name/description handling:

```python
if body.language is not None:
    fields.append("language = ?")
    values.append(body.language)
```

This goes right after the `if body.description is not None:` block.

**Step 4: Commit**

```bash
git add src/talekeeper/routers/campaigns.py
git commit -m "feat: add language field to campaign create/update API"
```

---

### Task 4: Session API — accept language, inherit from campaign

**Files:**
- Modify: `src/talekeeper/routers/sessions.py`

**Step 1: Add language to SessionCreate and SessionUpdate**

```python
class SessionCreate(BaseModel):
    name: str
    date: str
    language: str | None = None
```

```python
class SessionUpdate(BaseModel):
    name: str | None = None
    date: str | None = None
    status: str | None = None
    language: str | None = None
```

**Step 2: Update create_session to inherit language from campaign**

Replace the `create_session` function:

```python
@router.post("/api/campaigns/{campaign_id}/sessions")
async def create_session(campaign_id: int, body: SessionCreate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT id, language FROM campaigns WHERE id = ?", (campaign_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        language = body.language if body.language is not None else existing[0]["language"]

        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date, language) VALUES (?, ?, ?, ?)",
            (campaign_id, body.name, body.date, language),
        )
        session_id = cursor.lastrowid
        rows = await db.execute_fetchall(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
    return dict(rows[0])
```

**Step 3: Handle language in update_session**

Add language handling in the `update_session` function, after the `if body.status is not None:` block:

```python
if body.language is not None:
    fields.append("language = ?")
    values.append(body.language)
```

**Step 4: Commit**

```bash
git add src/talekeeper/routers/sessions.py
git commit -m "feat: add language field to session create/update, inherit from campaign"
```

---

### Task 5: Retranscribe API — accept and use language

**Files:**
- Modify: `src/talekeeper/routers/transcripts.py`

**Step 1: Add language to RetranscribeRequest**

```python
class RetranscribeRequest(BaseModel):
    model_size: str = "medium"
    language: str | None = None
```

**Step 2: Use language when calling transcribe**

In the `retranscribe` function, after fetching the session, determine the language and pass it:

After `audio_path = Path(session["audio_path"])`, add:

```python
language = body.language if body.language is not None else session.get("language", "en")
```

Then update the transcribe call:

```python
segments = transcribe(wav_path, model_size=body.model_size, language=language)
```

**Step 3: Commit**

```bash
git add src/talekeeper/routers/transcripts.py
git commit -m "feat: add language parameter to retranscribe endpoint"
```

---

### Task 6: Live recording — use session language

**Files:**
- Modify: `src/talekeeper/routers/recording.py`

**Step 1: Read session language and pass to transcription**

In `recording_ws`, after fetching the session (line 78: `session = dict(rows[0])`), the `session` dict already includes `language` from the DB. Store it:

```python
session_language = session.get("language", "en")
```

**Step 2: Update _run_transcription_on_chunk to accept language**

Change the function signature:

```python
async def _run_transcription_on_chunk(
    accumulated_audio: bytes, session_id: int, websocket: WebSocket, offset: float, language: str = "en"
) -> None:
```

And update the `transcribe` call inside it:

```python
segments = transcribe(wav_path, language=language)
```

**Step 3: Pass language when creating transcription task**

In `recording_ws`, update the `asyncio.create_task` call:

```python
asyncio.create_task(
    _run_transcription_on_chunk(
        accumulated, session_id, websocket, last_transcribed_offset, session_language
    )
)
```

**Step 4: Commit**

```bash
git add src/talekeeper/routers/recording.py
git commit -m "feat: use session language for live recording transcription"
```

---

### Task 7: Frontend — language constants file

**Files:**
- Create: `frontend/src/lib/languages.ts`

**Step 1: Create the Whisper languages list**

Create `frontend/src/lib/languages.ts` with all Whisper-supported languages:

```typescript
/** All languages supported by OpenAI Whisper / faster-whisper. */
export const WHISPER_LANGUAGES: { code: string; name: string }[] = [
  { code: "af", name: "Afrikaans" },
  { code: "am", name: "Amharic" },
  { code: "ar", name: "Arabic" },
  { code: "as", name: "Assamese" },
  { code: "az", name: "Azerbaijani" },
  { code: "ba", name: "Bashkir" },
  { code: "be", name: "Belarusian" },
  { code: "bg", name: "Bulgarian" },
  { code: "bn", name: "Bengali" },
  { code: "bo", name: "Tibetan" },
  { code: "br", name: "Breton" },
  { code: "bs", name: "Bosnian" },
  { code: "ca", name: "Catalan" },
  { code: "cs", name: "Czech" },
  { code: "cy", name: "Welsh" },
  { code: "da", name: "Danish" },
  { code: "de", name: "German" },
  { code: "el", name: "Greek" },
  { code: "en", name: "English" },
  { code: "es", name: "Spanish" },
  { code: "et", name: "Estonian" },
  { code: "eu", name: "Basque" },
  { code: "fa", name: "Persian" },
  { code: "fi", name: "Finnish" },
  { code: "fo", name: "Faroese" },
  { code: "fr", name: "French" },
  { code: "gl", name: "Galician" },
  { code: "gu", name: "Gujarati" },
  { code: "ha", name: "Hausa" },
  { code: "haw", name: "Hawaiian" },
  { code: "he", name: "Hebrew" },
  { code: "hi", name: "Hindi" },
  { code: "hr", name: "Croatian" },
  { code: "ht", name: "Haitian Creole" },
  { code: "hu", name: "Hungarian" },
  { code: "hy", name: "Armenian" },
  { code: "id", name: "Indonesian" },
  { code: "is", name: "Icelandic" },
  { code: "it", name: "Italian" },
  { code: "ja", name: "Japanese" },
  { code: "jw", name: "Javanese" },
  { code: "ka", name: "Georgian" },
  { code: "kk", name: "Kazakh" },
  { code: "km", name: "Khmer" },
  { code: "kn", name: "Kannada" },
  { code: "ko", name: "Korean" },
  { code: "la", name: "Latin" },
  { code: "lb", name: "Luxembourgish" },
  { code: "ln", name: "Lingala" },
  { code: "lo", name: "Lao" },
  { code: "lt", name: "Lithuanian" },
  { code: "lv", name: "Latvian" },
  { code: "mg", name: "Malagasy" },
  { code: "mi", name: "Maori" },
  { code: "mk", name: "Macedonian" },
  { code: "ml", name: "Malayalam" },
  { code: "mn", name: "Mongolian" },
  { code: "mr", name: "Marathi" },
  { code: "ms", name: "Malay" },
  { code: "mt", name: "Maltese" },
  { code: "my", name: "Myanmar" },
  { code: "ne", name: "Nepali" },
  { code: "nl", name: "Dutch" },
  { code: "nn", name: "Nynorsk" },
  { code: "no", name: "Norwegian" },
  { code: "oc", name: "Occitan" },
  { code: "pa", name: "Panjabi" },
  { code: "pl", name: "Polish" },
  { code: "ps", name: "Pashto" },
  { code: "pt", name: "Portuguese" },
  { code: "ro", name: "Romanian" },
  { code: "ru", name: "Russian" },
  { code: "sa", name: "Sanskrit" },
  { code: "sd", name: "Sindhi" },
  { code: "si", name: "Sinhala" },
  { code: "sk", name: "Slovak" },
  { code: "sl", name: "Slovenian" },
  { code: "sn", name: "Shona" },
  { code: "so", name: "Somali" },
  { code: "sq", name: "Albanian" },
  { code: "sr", name: "Serbian" },
  { code: "su", name: "Sundanese" },
  { code: "sv", name: "Swedish" },
  { code: "sw", name: "Swahili" },
  { code: "ta", name: "Tamil" },
  { code: "te", name: "Telugu" },
  { code: "tg", name: "Tajik" },
  { code: "th", name: "Thai" },
  { code: "tk", name: "Turkmen" },
  { code: "tl", name: "Tagalog" },
  { code: "tr", name: "Turkish" },
  { code: "tt", name: "Tatar" },
  { code: "uk", name: "Ukrainian" },
  { code: "ur", name: "Urdu" },
  { code: "uz", name: "Uzbek" },
  { code: "vi", name: "Vietnamese" },
  { code: "yi", name: "Yiddish" },
  { code: "yo", name: "Yoruba" },
  { code: "zh", name: "Chinese" },
];
```

**Step 2: Commit**

```bash
git add frontend/src/lib/languages.ts
git commit -m "feat: add Whisper supported languages list"
```

---

### Task 8: Frontend — LanguageSelect component

**Files:**
- Create: `frontend/src/components/LanguageSelect.svelte`

**Step 1: Create the searchable language dropdown**

Create `frontend/src/components/LanguageSelect.svelte`:

```svelte
<script lang="ts">
  import { WHISPER_LANGUAGES } from '../lib/languages';

  type Props = {
    value: string;
    onchange: (code: string) => void;
    compact?: boolean;
  };
  let { value, onchange, compact = false }: Props = $props();

  let search = $state('');
  let open = $state(false);
  let inputEl: HTMLInputElement | undefined = $state();

  let filtered = $derived(
    search
      ? WHISPER_LANGUAGES.filter(
          (l) =>
            l.name.toLowerCase().includes(search.toLowerCase()) ||
            l.code.toLowerCase().includes(search.toLowerCase())
        )
      : WHISPER_LANGUAGES
  );

  let selectedName = $derived(
    WHISPER_LANGUAGES.find((l) => l.code === value)?.name ?? value
  );

  function select(code: string) {
    onchange(code);
    search = '';
    open = false;
  }

  function handleFocus() {
    open = true;
    search = '';
  }

  function handleBlur() {
    // Delay to allow click on option
    setTimeout(() => { open = false; search = ''; }, 150);
  }
</script>

<div class="lang-select" class:compact>
  <input
    bind:this={inputEl}
    type="text"
    placeholder={selectedName}
    bind:value={search}
    onfocus={handleFocus}
    onblur={handleBlur}
  />
  {#if open}
    <ul class="dropdown">
      {#each filtered as lang}
        <li>
          <button
            class="option"
            class:selected={lang.code === value}
            onmousedown={() => select(lang.code)}
          >
            {lang.name} <span class="code">({lang.code})</span>
          </button>
        </li>
      {/each}
      {#if filtered.length === 0}
        <li class="no-results">No languages found</li>
      {/if}
    </ul>
  {/if}
</div>

<style>
  .lang-select {
    position: relative;
    width: 100%;
  }

  .lang-select.compact {
    width: auto;
    display: inline-block;
    min-width: 160px;
  }

  input {
    width: 100%;
    padding: 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.85rem;
    box-sizing: border-box;
  }

  .compact input {
    padding: 0.3rem 0.5rem;
    font-size: 0.8rem;
  }

  .dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    max-height: 200px;
    overflow-y: auto;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    margin: 2px 0 0;
    padding: 0;
    list-style: none;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .option {
    display: block;
    width: 100%;
    padding: 0.4rem 0.75rem;
    background: none;
    border: none;
    color: var(--text);
    font: inherit;
    font-size: 0.85rem;
    text-align: left;
    cursor: pointer;
  }

  .option:hover {
    background: var(--bg-hover);
  }

  .option.selected {
    color: var(--accent);
    font-weight: 600;
  }

  .code {
    color: var(--text-faint);
    font-size: 0.75rem;
  }

  .no-results {
    padding: 0.5rem 0.75rem;
    color: var(--text-muted);
    font-size: 0.85rem;
  }
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/LanguageSelect.svelte
git commit -m "feat: add searchable LanguageSelect component"
```

---

### Task 9: Frontend — add language to campaign create/edit

**Files:**
- Modify: `frontend/src/routes/CampaignList.svelte`

**Step 1: Add language state and import**

Add import at top of script:

```typescript
import LanguageSelect from '../components/LanguageSelect.svelte';
```

Add state variables after existing ones:

```typescript
let newLang = $state('en');
let editLang = $state('en');
```

Update the `Campaign` type to include language:

```typescript
type Campaign = { id: number; name: string; description: string; language: string; created_at: string };
```

**Step 2: Pass language in create and edit**

In `create()`, update the API call:

```typescript
await api.post('/campaigns', { name: newName, description: newDesc, language: newLang });
```

Reset `newLang` after creation:

```typescript
newLang = 'en';
```

In `startEdit()`, capture the language:

```typescript
editLang = c.language;
```

In `saveEdit()`, pass language:

```typescript
await api.put(`/campaigns/${editingId}`, { name: editName, description: editDesc, language: editLang });
```

**Step 3: Add LanguageSelect to create form**

In the template, inside the `{#if showCreate}` card, add after the textarea:

```svelte
<label class="field-label">Language</label>
<LanguageSelect value={newLang} onchange={(code) => (newLang = code)} />
```

**Step 4: Add LanguageSelect to edit form**

In the template, inside the `{#if editingId === c.id}` block, add after the textarea:

```svelte
<label class="field-label">Language</label>
<LanguageSelect value={editLang} onchange={(code) => (editLang = code)} />
```

**Step 5: Add field-label style**

Add to the `<style>` block:

```css
.field-label {
  display: block;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
}
```

**Step 6: Commit**

```bash
git add frontend/src/routes/CampaignList.svelte
git commit -m "feat: add language selector to campaign create/edit forms"
```

---

### Task 10: Frontend — add language to session creation

**Files:**
- Modify: `frontend/src/routes/CampaignDashboard.svelte`

**Step 1: Add import and state**

Add import at top:

```typescript
import LanguageSelect from '../components/LanguageSelect.svelte';
```

Update Campaign type to include language:

```typescript
type Campaign = { id: number; name: string; description: string; language: string };
```

Add state variable after existing new session vars:

```typescript
let newSessionLang = $state('en');
```

**Step 2: Sync language default when campaign loads**

Add an `$effect` to sync the default language when the campaign loads:

```typescript
$effect(() => {
  if (campaign) {
    newSessionLang = campaign.language;
  }
});
```

**Step 3: Pass language in createSession**

Update the API call in `createSession()`:

```typescript
await api.post(`/campaigns/${campaignId}/sessions`, {
  name: newSessionName,
  date: newSessionDate,
  language: newSessionLang,
});
```

**Step 4: Add LanguageSelect to the new session form**

In the template, inside `{#if showNewSession}`, add after the date input:

```svelte
<label class="field-label">Language</label>
<LanguageSelect value={newSessionLang} onchange={(code) => (newSessionLang = code)} />
```

**Step 5: Add field-label style**

Add to the `<style>` block:

```css
.field-label {
  display: block;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
}
```

**Step 6: Commit**

```bash
git add frontend/src/routes/CampaignDashboard.svelte
git commit -m "feat: add language selector to session creation form"
```

---

### Task 11: Frontend — add language to retranscribe

**Files:**
- Modify: `frontend/src/components/TranscriptView.svelte`

**Step 1: Add import and props**

Add import at top:

```typescript
import LanguageSelect from './LanguageSelect.svelte';
```

Add `language` to Props type and destructuring:

```typescript
type Props = {
  sessionId: number;
  isRecording?: boolean;
  hasAudio?: boolean;
  language?: string;
  onSegmentClick?: (startTime: number) => void;
};
let { sessionId, isRecording = false, hasAudio = false, language = 'en', onSegmentClick }: Props = $props();
```

Add state for the retranscribe language override:

```typescript
let retranscribeLang = $state('en');
```

Add an `$effect` to sync it with the session language:

```typescript
$effect(() => { retranscribeLang = language; });
```

**Step 2: Pass language in retranscribe call**

Update the `retranscribe()` function:

```typescript
await api.post(`/sessions/${sessionId}/retranscribe`, { language: retranscribeLang });
```

**Step 3: Add LanguageSelect next to retranscribe buttons**

For the primary retranscribe button (empty state), add the language select before the button:

```svelte
{#if hasAudio && !isRecording}
  <div class="retranscribe-controls">
    <LanguageSelect compact value={retranscribeLang} onchange={(code) => (retranscribeLang = code)} />
    <button class="retranscribe-btn primary" onclick={retranscribe}>
      Retranscribe
    </button>
  </div>
{/if}
```

For the toolbar retranscribe button (when segments exist):

```svelte
{#if hasAudio}
  <div class="toolbar">
    <LanguageSelect compact value={retranscribeLang} onchange={(code) => (retranscribeLang = code)} />
    <button class="retranscribe-btn secondary" onclick={retranscribe}>
      Retranscribe
    </button>
  </div>
{/if}
```

**Step 4: Add styles for retranscribe-controls**

```css
.retranscribe-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: center;
  margin-top: 0.75rem;
}
```

**Step 5: Commit**

```bash
git add frontend/src/components/TranscriptView.svelte
git commit -m "feat: add language selector to retranscribe UI"
```

---

### Task 12: Frontend — pass session language from SessionDetail

**Files:**
- Modify: `frontend/src/routes/SessionDetail.svelte`

**Step 1: Add language to Session type**

Update the Session type:

```typescript
type Session = { id: number; campaign_id: number; name: string; date: string; status: string; audio_path: string | null; language: string };
```

**Step 2: Pass language to TranscriptView**

Update the `<TranscriptView>` component call:

```svelte
<TranscriptView
  sessionId={sessionId}
  isRecording={session.status === 'recording'}
  {hasAudio}
  language={session.language}
  onSegmentClick={handleSegmentClick}
/>
```

**Step 3: Display current language in session header**

Update the meta span:

```svelte
<span class="meta">{session.date} &middot; {session.status} &middot; {session.language.toUpperCase()}</span>
```

**Step 4: Commit**

```bash
git add frontend/src/routes/SessionDetail.svelte
git commit -m "feat: pass session language to TranscriptView and display in header"
```

---

### Task 13: Manual smoke test

**Step 1: Start the application**

Run the app and verify:

1. Create a new campaign — language dropdown appears, defaults to English
2. Edit a campaign — can change language
3. Create a session under the campaign — language pre-fills from campaign default
4. Go to session detail — language code shows in header
5. Click Retranscribe — language dropdown appears pre-filled with session language, can be changed

**Step 2: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: address issues found during smoke test"
```
