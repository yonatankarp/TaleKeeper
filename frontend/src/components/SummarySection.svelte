<script lang="ts">
  import { api } from '../lib/api';
  import ConfirmDialog from './ConfirmDialog.svelte';
  import Spinner from './Spinner.svelte';

  type Props = { sessionId: number };
  let { sessionId }: Props = $props();

  type Summary = {
    id: number;
    type: string;
    content: string;
    model_used: string;
    generated_at: string;
    character_name?: string;
    player_name?: string;
  };

  let summaries = $state<Summary[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let editingId = $state<number | null>(null);
  let editContent = $state('');
  let llmOk = $state<boolean | null>(null);
  let llmMsg = $state('');
  let confirmRegenType = $state<string | null>(null);
  let confirmDeleteId = $state<number | null>(null);
  let genElapsed = $state(0);
  let genTimer: ReturnType<typeof setInterval> | null = null;

  function startGenTimer() {
    genElapsed = 0;
    genTimer = setInterval(() => { genElapsed += 1; }, 1000);
  }

  function stopGenTimer() {
    if (genTimer) { clearInterval(genTimer); genTimer = null; }
  }

  async function load() {
    summaries = await api.get<Summary[]>(`/sessions/${sessionId}/summaries`);
  }

  async function checkLlm() {
    try {
      const status = await api.get<{ status: string; message?: string }>('/llm/status');
      llmOk = status.status === 'ok';
      llmMsg = status.message ?? '';
    } catch {
      llmOk = false;
      llmMsg = 'Cannot reach LLM provider';
    }
  }

  async function generateFull() {
    loading = true;
    error = null;
    startGenTimer();
    try {
      await api.post(`/sessions/${sessionId}/generate-summary`, { type: 'full' });
      await load();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
      stopGenTimer();
    }
  }

  async function generatePov() {
    loading = true;
    error = null;
    startGenTimer();
    try {
      await api.post(`/sessions/${sessionId}/generate-summary`, { type: 'pov' });
      await load();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
      stopGenTimer();
    }
  }

  async function regenerate(type: string) {
    confirmRegenType = null;
    loading = true;
    error = null;
    startGenTimer();
    try {
      await api.post(`/sessions/${sessionId}/regenerate-summary`, { type });
      await load();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
      stopGenTimer();
    }
  }

  function startEdit(s: Summary) {
    editingId = s.id;
    editContent = s.content;
  }

  async function saveEdit() {
    if (editingId === null) return;
    await api.put(`/summaries/${editingId}`, { content: editContent });
    editingId = null;
    await load();
  }

  async function deleteSummary(id: number) {
    await api.del(`/summaries/${id}`);
    confirmDeleteId = null;
    await load();
  }

  $effect(() => { load(); checkLlm(); });

  let fullSummaries = $derived(summaries.filter(s => s.type === 'full'));
  let povSummaries = $derived(summaries.filter(s => s.type === 'pov'));
</script>

<div class="summary-section">
  {#if error}
    <div class="error">{error}</div>
  {/if}

  {#if llmOk === false}
    <div class="warning">
      <strong>LLM provider not available</strong>
      <p>{llmMsg || 'No LLM provider is reachable. Check the base URL and API key in Settings.'}</p>
    </div>
  {/if}

  <div class="actions">
    <button class="btn btn-primary" onclick={generateFull} disabled={loading || llmOk === false}>
      {#if loading}
        <Spinner size="14px" /> Generating... ({genElapsed}s)
      {:else}
        Generate Summary
      {/if}
    </button>
    <button class="btn btn-primary" onclick={generatePov} disabled={loading || llmOk === false}>
      {#if loading}
        <Spinner size="14px" /> Generating... ({genElapsed}s)
      {:else}
        Generate POV Summaries
      {/if}
    </button>
  </div>

  <div class="gen-hint">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
    Summary generation may take a few minutes, especially for longer sessions. Please be patient while the tale is being crafted.
  </div>

  {#if fullSummaries.length > 0}
    <h3>Session Summary</h3>
    {#each fullSummaries as s}
      <div class="summary-card">
        {#if editingId === s.id}
          <textarea class="edit-area" bind:value={editContent}></textarea>
          <div class="btn-group">
            <button class="btn btn-primary btn-sm" onclick={saveEdit}>Save</button>
            <button class="btn btn-sm" onclick={() => (editingId = null)}>Cancel</button>
          </div>
        {:else}
          <div class="summary-content">{s.content}</div>
          <div class="summary-meta">
            <span>Model: {s.model_used}</span>
            <span>Generated: {s.generated_at}</span>
          </div>
          <div class="btn-group">
            <button class="btn btn-sm" onclick={() => startEdit(s)}>Edit</button>
            <button class="btn btn-sm" onclick={() => (confirmRegenType = 'full')}>Regenerate</button>
            <button class="btn btn-sm btn-danger" onclick={() => (confirmDeleteId = s.id)}>Delete</button>
          </div>
        {/if}
      </div>
    {/each}
  {/if}

  {#if povSummaries.length > 0}
    <h3>Character POV Summaries</h3>
    {#each povSummaries as s}
      <div class="summary-card">
        <h4>{s.character_name ?? 'Unknown'} {s.player_name ? `(${s.player_name})` : ''}</h4>
        {#if editingId === s.id}
          <textarea class="edit-area" bind:value={editContent}></textarea>
          <div class="btn-group">
            <button class="btn btn-primary btn-sm" onclick={saveEdit}>Save</button>
            <button class="btn btn-sm" onclick={() => (editingId = null)}>Cancel</button>
          </div>
        {:else}
          <div class="summary-content">{s.content}</div>
          <div class="summary-meta">
            <span>Model: {s.model_used}</span>
            <span>Generated: {s.generated_at}</span>
          </div>
          <div class="btn-group">
            <button class="btn btn-sm" onclick={() => startEdit(s)}>Edit</button>
            <button class="btn btn-sm btn-danger" onclick={() => (confirmDeleteId = s.id)}>Delete</button>
          </div>
        {/if}
      </div>
    {/each}
    <button class="btn btn-sm" onclick={() => (confirmRegenType = 'pov')}>Regenerate All POV</button>
  {/if}

  {#if summaries.length === 0 && !loading}
    <p class="empty">No summaries generated yet. Generate a summary after your session is transcribed.</p>
  {/if}
</div>

{#if confirmRegenType !== null}
  <ConfirmDialog
    title="Regenerate Summaries"
    message="This will replace existing {confirmRegenType} summaries with newly generated ones."
    confirmLabel="Regenerate"
    onconfirm={() => regenerate(confirmRegenType!)}
    oncancel={() => (confirmRegenType = null)}
  />
{/if}

{#if confirmDeleteId !== null}
  <ConfirmDialog
    title="Delete Summary"
    message="Are you sure you want to delete this summary?"
    confirmLabel="Delete"
    onconfirm={() => deleteSummary(confirmDeleteId!)}
    oncancel={() => (confirmDeleteId = null)}
  />
{/if}

<style>
  .summary-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .error {
    background: var(--error-bg);
    border: 1px solid var(--danger);
    color: var(--danger);
    padding: 0.75rem;
    border-radius: 4px;
    font-size: 0.9rem;
  }

  .warning {
    background: var(--warning-bg);
    border: 1px solid var(--warning);
    color: var(--warning);
    padding: 0.75rem;
    border-radius: 4px;
    font-size: 0.9rem;
  }


  .actions {
    display: flex;
    gap: 0.75rem;
  }

  .summary-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
  }

  .summary-card h4 {
    margin: 0 0 0.5rem;
    color: var(--accent);
  }

  .summary-content {
    white-space: pre-wrap;
    line-height: 1.6;
    font-size: 0.9rem;
    margin-bottom: 0.75rem;
  }

  .summary-meta {
    display: flex;
    gap: 1rem;
    font-size: 0.75rem;
    color: var(--text-faint);
    margin-bottom: 0.5rem;
  }

  .edit-area {
    width: 100%;
    min-height: 200px;
    padding: 0.75rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.9rem;
    resize: vertical;
    box-sizing: border-box;
    margin-bottom: 0.5rem;
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
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
  .btn-danger { color: var(--danger); }
  .btn-sm { padding: 0.25rem 0.75rem; font-size: 0.8rem; }
  .btn-group { display: flex; gap: 0.5rem; }

  .gen-hint {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: var(--warning);
    background: var(--warning-bg);
    border: 1px solid var(--warning);
    border-radius: 6px;
    padding: 0.6rem 1rem;
    margin: 0;
  }

  .gen-hint svg {
    flex-shrink: 0;
  }

  .empty { color: var(--text-faint); text-align: center; padding: 2rem; }
</style>
