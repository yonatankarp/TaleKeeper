<script lang="ts">
  import { api } from '../lib/api';
  import { navigate } from '../lib/router.svelte';
  import LanguageSelect from '../components/LanguageSelect.svelte';
  import Spinner from '../components/Spinner.svelte';
  import ConfirmDialog from '../components/ConfirmDialog.svelte';

  type Campaign = { id: number; name: string; description: string; language: string; created_at: string };

  let campaigns = $state<Campaign[]>([]);
  let pageLoading = $state(true);
  let showCreate = $state(false);
  let newName = $state('');
  let newDesc = $state('');
  let editingId = $state<number | null>(null);
  let editName = $state('');
  let editDesc = $state('');
  let newLang = $state('en');
  let editLang = $state('en');
  let confirmDeleteId = $state<number | null>(null);
  let createNameError = $state(false);

  async function load() {
    campaigns = await api.get<Campaign[]>('/campaigns');
    pageLoading = false;
  }

  async function create() {
    if (!newName.trim()) {
      createNameError = true;
      return;
    }
    createNameError = false;
    await api.post('/campaigns', { name: newName, description: newDesc, language: newLang });
    newName = '';
    newDesc = '';
    newLang = 'en';
    showCreate = false;
    await load();
  }

  async function startEdit(c: Campaign) {
    editingId = c.id;
    editName = c.name;
    editDesc = c.description;
    editLang = c.language;
  }

  async function saveEdit() {
    if (editingId === null) return;
    await api.put(`/campaigns/${editingId}`, { name: editName, description: editDesc, language: editLang });
    editingId = null;
    await load();
  }

  async function remove(id: number) {
    await api.del(`/campaigns/${id}`);
    confirmDeleteId = null;
    await load();
  }

  $effect(() => { load(); });
</script>

{#if pageLoading}
  <div class="loading"><Spinner /> Loading campaigns...</div>
{:else}
<div class="page">
  <div class="page-header">
    <h2>Campaigns</h2>
    <button class="btn btn-primary" onclick={() => (showCreate = true)}>New Campaign</button>
  </div>

  {#if showCreate}
    <div class="card form-card">
      <input type="text" placeholder="Campaign name" bind:value={newName} class:input-error={createNameError} oninput={() => (createNameError = false)} />
      {#if createNameError}<p class="field-error">Campaign name is required</p>{/if}
      <textarea placeholder="Description (optional)" bind:value={newDesc}></textarea>
      <label class="field-label">Language</label>
      <LanguageSelect value={newLang} onchange={(code) => (newLang = code)} />
      <div class="btn-group">
        <button class="btn btn-primary" onclick={create}>Create</button>
        <button class="btn" onclick={() => (showCreate = false)}>Cancel</button>
      </div>
    </div>
  {/if}

  <div class="campaign-grid">
    {#each campaigns as c}
      <div class="card">
        {#if editingId === c.id}
          <input type="text" bind:value={editName} />
          <textarea bind:value={editDesc}></textarea>
          <label class="field-label">Language</label>
          <LanguageSelect value={editLang} onchange={(code) => (editLang = code)} />
          <div class="btn-group">
            <button class="btn btn-primary" onclick={saveEdit}>Save</button>
            <button class="btn" onclick={() => (editingId = null)}>Cancel</button>
          </div>
        {:else}
          <button class="card-title" onclick={() => navigate(`/campaigns/${c.id}`)}>{c.name}</button>
          {#if c.description}
            <p class="card-desc">{c.description}</p>
          {/if}
          <div class="btn-group">
            <button class="btn btn-sm" onclick={() => startEdit(c)}>Edit</button>
            <button class="btn btn-sm btn-danger" onclick={() => (confirmDeleteId = c.id)}>Delete</button>
          </div>
        {/if}
      </div>
    {/each}
  </div>

  {#if campaigns.length === 0 && !showCreate}
    <p class="empty">No campaigns yet. Create your first campaign to start recording sessions.</p>
  {/if}
</div>
{/if}

{#if confirmDeleteId !== null}
  <ConfirmDialog
    title="Delete Campaign"
    message="This will permanently delete this campaign and all its sessions, transcripts, and audio. This cannot be undone."
    confirmLabel="Delete"
    onconfirm={() => remove(confirmDeleteId!)}
    oncancel={() => (confirmDeleteId = null)}
  />
{/if}

<style>
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .campaign-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }

  .card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
  }

  .form-card {
    margin-bottom: 1.5rem;
  }

  .card-title {
    margin: 0 0 0.5rem;
    cursor: pointer;
    color: var(--accent);
    background: none;
    border: none;
    padding: 0;
    font-size: 1.17rem;
    font-weight: bold;
    text-align: left;
  }

  .card-title:hover {
    text-decoration: underline;
  }

  .card-desc {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin: 0 0 1rem;
  }

  input, textarea {
    width: 100%;
    padding: 0.5rem;
    margin-bottom: 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    box-sizing: border-box;
  }

  textarea {
    min-height: 60px;
    resize: vertical;
  }

  .btn {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-surface);
    color: var(--text);
    cursor: pointer;
    font-size: 0.85rem;
  }

  .btn:hover { background: var(--bg-hover); }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); }
  .btn-danger { color: var(--accent); }
  .btn-sm { padding: 0.25rem 0.75rem; font-size: 0.8rem; }
  .btn-group { display: flex; gap: 0.5rem; }

  .field-label {
    display: block;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
  }

  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 3rem;
    color: var(--text-muted);
  }

  .input-error {
    border-color: var(--accent) !important;
  }

  .field-error {
    color: var(--accent);
    font-size: 0.8rem;
    margin: -0.25rem 0 0.5rem;
  }

  .empty {
    text-align: center;
    color: var(--text-muted);
    margin-top: 3rem;
  }
</style>
