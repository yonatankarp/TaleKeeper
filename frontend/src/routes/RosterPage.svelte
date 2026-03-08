<script lang="ts">
  import { api } from '../lib/api';
  import Spinner from '../components/Spinner.svelte';
  import ConfirmDialog from '../components/ConfirmDialog.svelte';

  type Props = { campaignId: number };
  let { campaignId }: Props = $props();

  type RosterEntry = { id: number; player_name: string; character_name: string; description: string; sheet_url: string; sheet_data: string; is_active: number };
  type VoiceSig = { id: number; roster_entry_id: number; num_samples: number; created_at: string };

  let entries = $state<RosterEntry[]>([]);
  let voiceSigs = $state<Map<number, VoiceSig>>(new Map());
  let pageLoading = $state(true);
  let newPlayer = $state('');
  let newCharacter = $state('');
  let newDescription = $state('');
  let editingId = $state<number | null>(null);
  let editPlayer = $state('');
  let editCharacter = $state('');
  let editDescription = $state('');
  let confirmRemoveId = $state<number | null>(null);
  let uploadingId = $state<number | null>(null);
  let importingId = $state<number | null>(null);
  let refreshingId = $state<number | null>(null);
  let voiceUploadingId = $state<number | null>(null);
  let urlInputId = $state<number | null>(null);
  let urlValue = $state('');
  let uploadError = $state<string | null>(null);

  async function load() {
    const [roster, sigs] = await Promise.all([
      api.get<RosterEntry[]>(`/campaigns/${campaignId}/roster`),
      api.get<VoiceSig[]>(`/campaigns/${campaignId}/voice-signatures`),
    ]);
    entries = roster;
    voiceSigs = new Map(sigs.map(s => [s.roster_entry_id, s]));
    pageLoading = false;
  }

  async function add() {
    if (!newPlayer.trim() || !newCharacter.trim()) return;
    await api.post(`/campaigns/${campaignId}/roster`, {
      player_name: newPlayer,
      character_name: newCharacter,
      description: newDescription,
    });
    newPlayer = '';
    newCharacter = '';
    newDescription = '';
    await load();
  }

  function startEdit(e: RosterEntry) {
    editingId = e.id;
    editPlayer = e.player_name;
    editCharacter = e.character_name;
    editDescription = e.description ?? '';
  }

  async function saveEdit() {
    if (editingId === null) return;
    await api.put(`/roster/${editingId}`, {
      player_name: editPlayer,
      character_name: editCharacter,
      description: editDescription,
    });
    editingId = null;
    await load();
  }

  async function toggleActive(e: RosterEntry) {
    await api.put(`/roster/${e.id}`, { is_active: !e.is_active });
    await load();
  }

  async function remove(id: number) {
    await api.del(`/roster/${id}`);
    confirmRemoveId = null;
    await load();
  }

  async function uploadSheet(entryId: number, file: File) {
    uploadingId = entryId;
    uploadError = null;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const resp = await fetch(`/api/roster/${entryId}/upload-sheet`, {
        method: 'POST',
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
      }
      await load();
    } catch (e: any) {
      uploadError = e.message;
    } finally {
      uploadingId = null;
    }
  }

  function triggerUpload(entryId: number) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf';
    input.onchange = () => {
      if (input.files?.[0]) uploadSheet(entryId, input.files[0]);
    };
    input.click();
  }

  function showUrlInput(entryId: number) {
    urlInputId = entryId;
    urlValue = '';
    uploadError = null;
  }

  async function importUrl(entryId: number) {
    if (!urlValue.trim()) return;
    importingId = entryId;
    uploadError = null;
    try {
      await api.post(`/roster/${entryId}/import-url`, { url: urlValue.trim() });
      urlInputId = null;
      urlValue = '';
      await load();
    } catch (e: any) {
      uploadError = e.message;
    } finally {
      importingId = null;
    }
  }

  async function refreshSheet(entryId: number) {
    refreshingId = entryId;
    uploadError = null;
    try {
      await api.post(`/roster/${entryId}/refresh-sheet`);
      await load();
    } catch (e: any) {
      uploadError = e.message;
    } finally {
      refreshingId = null;
    }
  }

  async function uploadVoiceSample(entryId: number, file: File) {
    voiceUploadingId = entryId;
    uploadError = null;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const resp = await fetch(`/api/roster/${entryId}/upload-voice-sample`, {
        method: 'POST',
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
      }
      await load();
    } catch (e: any) {
      uploadError = e.message;
    } finally {
      voiceUploadingId = null;
    }
  }

  function triggerVoiceUpload(entryId: number) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'audio/*';
    input.onchange = () => {
      if (input.files?.[0]) uploadVoiceSample(entryId, input.files[0]);
    };
    input.click();
  }

  let busy = $derived(uploadingId !== null || importingId !== null || refreshingId !== null || voiceUploadingId !== null);

  $effect(() => { load(); });
</script>

{#if pageLoading}
  <div class="loading"><Spinner /> Loading party...</div>
{:else}
<div class="page">
  <h2>Party</h2>

  <div class="add-form card">
    <div class="form-row">
      <input type="text" placeholder="Player name" bind:value={newPlayer} />
      <input type="text" placeholder="Character name" bind:value={newCharacter} />
      <button class="btn btn-primary" onclick={add}>Add</button>
    </div>
    <textarea
      class="description-input"
      placeholder="Character description (e.g. Half-elf ranger with a wolf companion, scarred face, wears a green cloak)"
      bind:value={newDescription}
      rows="2"
    ></textarea>
  </div>

  {#if uploadError}
    <div class="error">{uploadError}</div>
  {/if}

  <div class="roster-list">
    {#each entries as e}
      <div class="card roster-entry" class:inactive={!e.is_active}>
        {#if editingId === e.id}
          <div class="edit-form">
            <div class="form-row">
              <input type="text" bind:value={editPlayer} />
              <input type="text" bind:value={editCharacter} />
              <button class="btn btn-primary btn-sm" onclick={saveEdit}>Save</button>
              <button class="btn btn-sm" onclick={() => (editingId = null)}>Cancel</button>
            </div>
            <textarea
              class="description-input"
              placeholder="Character description..."
              bind:value={editDescription}
              rows="2"
            ></textarea>
          </div>
        {:else}
          <div class="entry-content">
            <div class="entry-header">
              <div class="entry-info">
                <strong>{e.character_name}</strong>
                <span class="player-label">({e.player_name})</span>
                {#if !e.is_active}<span class="inactive-badge">Inactive</span>{/if}
                {#if voiceSigs.has(e.id)}<span class="sig-badge" title="Voice signature stored ({voiceSigs.get(e.id)!.num_samples} samples)">Voice ID</span>{/if}
              </div>
              <div class="btn-group">
                <button class="btn btn-sm btn-voice" onclick={() => triggerVoiceUpload(e.id)} disabled={busy}>
                  {#if voiceUploadingId === e.id}
                    <Spinner size="12px" /> Processing...
                  {:else}
                    {voiceSigs.has(e.id) ? 'Replace Voice' : 'Upload Voice'}
                  {/if}
                </button>
                <button class="btn btn-sm btn-upload" onclick={() => triggerUpload(e.id)} disabled={busy}>
                  {#if uploadingId === e.id}
                    <Spinner size="12px" /> Extracting...
                  {:else}
                    Upload PDF
                  {/if}
                </button>
                <button class="btn btn-sm btn-upload" onclick={() => showUrlInput(e.id)} disabled={busy}>
                  Import URL
                </button>
                {#if e.sheet_url || e.sheet_data}
                  <button class="btn btn-sm btn-refresh" onclick={() => refreshSheet(e.id)} disabled={busy}>
                    {#if refreshingId === e.id}
                      <Spinner size="12px" /> Refreshing...
                    {:else}
                      Refresh
                    {/if}
                  </button>
                {/if}
                <button class="btn btn-sm" onclick={() => toggleActive(e)}>
                  {e.is_active ? 'Deactivate' : 'Activate'}
                </button>
                <button class="btn btn-sm" onclick={() => startEdit(e)}>Edit</button>
                <button class="btn btn-sm btn-danger" onclick={() => (confirmRemoveId = e.id)}>Remove</button>
              </div>
            </div>
            {#if urlInputId === e.id}
              <div class="url-input-row">
                <input
                  type="url"
                  class="url-input"
                  placeholder="https://www.dndbeyond.com/characters/..."
                  bind:value={urlValue}
                  disabled={importingId !== null}
                />
                <button class="btn btn-sm btn-primary" onclick={() => importUrl(e.id)} disabled={importingId !== null || !urlValue.trim()}>
                  {#if importingId === e.id}
                    <Spinner size="12px" /> Importing...
                  {:else}
                    Go
                  {/if}
                </button>
                <button class="btn btn-sm" onclick={() => (urlInputId = null)} disabled={importingId !== null}>Cancel</button>
              </div>
            {/if}
            {#if e.description}
              <p class="entry-description">{e.description}</p>
            {/if}
            {#if e.sheet_url}
              <span class="sheet-source">Source: <a href={e.sheet_url} target="_blank" rel="noopener">{e.sheet_url.length > 60 ? e.sheet_url.slice(0, 60) + '...' : e.sheet_url}</a></span>
            {:else if e.sheet_data}
              <span class="sheet-source">Source: uploaded PDF</span>
            {/if}
          </div>
        {/if}
      </div>
    {/each}
  </div>

  {#if entries.length === 0}
    <p class="empty">No players in the party yet. Add your party members above to use them for speaker identification.</p>
  {/if}
</div>
{/if}

{#if confirmRemoveId !== null}
  <ConfirmDialog
    title="Remove Party Member"
    message="Remove this player and character from the party?"
    confirmLabel="Remove"
    onconfirm={() => remove(confirmRemoveId!)}
    oncancel={() => (confirmRemoveId = null)}
  />
{/if}

<style>
  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 3rem;
    color: var(--text-muted);
  }

  .add-form { margin-bottom: 1.5rem; }

  .form-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .roster-list { display: flex; flex-direction: column; gap: 0.5rem; }

  .roster-entry {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem 1rem;
  }

  .roster-entry.inactive { opacity: 0.5; }

  .entry-content { display: flex; flex-direction: column; gap: 0.4rem; }

  .entry-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .edit-form { display: flex; flex-direction: column; gap: 0.5rem; }

  .entry-info { display: flex; align-items: center; gap: 0.5rem; }

  .entry-description {
    margin: 0;
    font-size: 0.85rem;
    color: var(--text-muted);
    line-height: 1.4;
  }

  .description-input {
    width: 100%;
    padding: 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.85rem;
    resize: vertical;
    box-sizing: border-box;
    margin-top: 0.5rem;
  }
  .player-label { color: var(--text-muted); }
  .inactive-badge {
    font-size: 0.7rem;
    background: var(--badge-dark);
    color: var(--text-muted);
    padding: 0.15rem 0.4rem;
    border-radius: 8px;
  }
  .sig-badge {
    font-size: 0.7rem;
    background: color-mix(in srgb, var(--accent) 15%, transparent);
    color: var(--accent);
    border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent);
    padding: 0.15rem 0.4rem;
    border-radius: 8px;
  }

  .card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }

  input {
    padding: 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
  }

  .btn {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-surface);
    color: var(--text);
    cursor: pointer;
    font-size: 0.85rem;
    white-space: nowrap;
  }

  .btn:hover { background: var(--bg-hover); }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); }
  .btn-upload { border-color: var(--accent); color: var(--accent); }
  .btn-upload:hover:not(:disabled) { background: var(--accent); color: #fff; }
  .btn-voice { border-color: var(--accent); color: var(--accent); }
  .btn-voice:hover:not(:disabled) { background: var(--accent); color: #fff; }
  .btn-refresh { border-color: var(--text-muted); color: var(--text-muted); }
  .btn-refresh:hover:not(:disabled) { background: var(--text-muted); color: #fff; }
  .btn-danger { color: var(--danger); }
  .btn-sm { padding: 0.25rem 0.75rem; font-size: 0.8rem; }
  .btn-group { display: flex; gap: 0.5rem; flex-wrap: wrap; }

  .url-input-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    margin-top: 0.25rem;
  }

  .url-input {
    flex: 1;
    padding: 0.4rem 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.85rem;
  }

  .sheet-source {
    font-size: 0.75rem;
    color: var(--text-faint);
  }

  .sheet-source a {
    color: var(--accent);
    text-decoration: none;
  }

  .sheet-source a:hover { text-decoration: underline; }

  .error {
    background: var(--error-bg);
    border: 1px solid var(--danger);
    color: var(--danger);
    padding: 0.75rem;
    border-radius: 4px;
    font-size: 0.9rem;
  }

  .empty { text-align: center; color: var(--text-muted); margin-top: 2rem; }
</style>
