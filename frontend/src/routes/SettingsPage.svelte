<script lang="ts">
  import { api } from '../lib/api';
  import Spinner from '../components/Spinner.svelte';

  let settings = $state<Record<string, string>>({});
  let pageLoading = $state(true);
  let toast = $state<string | null>(null);
  let testingOllama = $state(false);
  let ollamaResult = $state<string | null>(null);

  const whisperModels = ['tiny', 'base', 'small', 'medium', 'large-v3'];

  async function load() {
    settings = await api.get<Record<string, string>>('/settings');
    if (!settings.whisper_model) settings.whisper_model = 'medium';
    if (!settings.ollama_model) settings.ollama_model = 'llama3.1:8b';
    if (!settings.live_transcription) settings.live_transcription = 'false';
    pageLoading = false;
  }

  async function save() {
    await api.put('/settings', { settings });
    showToast('Settings saved');
  }

  async function testOllama() {
    testingOllama = true;
    try {
      const status = await api.get<{ status: string; message?: string }>('/ollama/status');
      ollamaResult = status.status === 'ok'
        ? 'Connected! Ollama is running.'
        : `Error: ${status.message}`;
    } catch {
      ollamaResult = 'Cannot reach Ollama. Is it running?';
    } finally {
      testingOllama = false;
    }
  }

  function showToast(msg: string) {
    toast = msg;
    setTimeout(() => { toast = null; }, 3000);
  }

  $effect(() => { load(); });
</script>

{#if pageLoading}
  <div class="loading"><Spinner /> Loading settings...</div>
{:else}
<div class="page">
  <h2>Settings</h2>

  {#if toast}
    <div class="toast">{toast}</div>
  {/if}

  <div class="section">
    <h3>Transcription</h3>
    <label>
      Whisper Model
      <select bind:value={settings.whisper_model}>
        {#each whisperModels as m}
          <option value={m}>{m}</option>
        {/each}
      </select>
    </label>
    <label class="checkbox-label">
      <input type="checkbox" checked={settings.live_transcription === 'true'} onchange={(e: Event) => { settings.live_transcription = (e.target as HTMLInputElement).checked ? 'true' : 'false'; }} />
      Live transcription during recording
    </label>
    <p class="hint">When enabled, preview segments appear during recording. These are preliminary — the final transcript may differ after full processing (improved accuracy, speaker labels, etc.).</p>
  </div>

  <div class="section">
    <h3>Summary Generation (Ollama)</h3>
    <label>
      Model Name
      <input type="text" bind:value={settings.ollama_model} placeholder="llama3.1:8b" />
    </label>
    <div class="action-row">
      <button class="btn" onclick={testOllama} disabled={testingOllama}>
        {testingOllama ? 'Testing...' : 'Test Connection'}
      </button>
      {#if ollamaResult}
        <span class="test-result">{ollamaResult}</span>
      {/if}
    </div>
  </div>

  <div class="section">
    <h3>Email (SMTP)</h3>
    <label>
      SMTP Host
      <input type="text" bind:value={settings.smtp_host} placeholder="smtp.gmail.com" />
    </label>
    <label>
      SMTP Port
      <input type="text" bind:value={settings.smtp_port} placeholder="587" />
    </label>
    <label>
      Username
      <input type="text" bind:value={settings.smtp_username} placeholder="you@example.com" />
    </label>
    <label>
      Password
      <input type="password" bind:value={settings.smtp_password} placeholder="app password" />
    </label>
    <label>
      Sender Address
      <input type="text" bind:value={settings.smtp_sender} placeholder="you@example.com" />
    </label>
  </div>

  <div class="section">
    <h3>Data</h3>
    <p class="info">Your data is stored at: <code>data/</code> in the application directory. Back up this folder to preserve your recordings, transcripts, and summaries.</p>
  </div>

  <button class="btn btn-primary" onclick={save}>Save Settings</button>
</div>
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

  .section {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1.25rem;
  }

  .section h3 { margin: 0 0 0.75rem; }

  label {
    display: block;
    margin-bottom: 0.75rem;
    font-size: 0.85rem;
    color: var(--text-secondary);
  }

  input, select {
    display: block;
    width: 100%;
    padding: 0.5rem;
    margin-top: 0.25rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    box-sizing: border-box;
  }

  select { cursor: pointer; }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: var(--text);
    cursor: pointer;
  }

  .checkbox-label input[type="checkbox"] {
    width: auto;
    margin: 0;
  }

  .hint {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin: 0.25rem 0 0;
  }

  .action-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .test-result { font-size: 0.85rem; color: var(--text-secondary); }

  .info {
    color: var(--text-muted);
    font-size: 0.9rem;
  }

  .info code {
    background: var(--bg-input);
    padding: 0.15rem 0.4rem;
    border-radius: 3px;
  }

  .toast {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    background: var(--success);
    color: #fff;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    z-index: 1000;
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
  .btn-primary:hover { background: var(--accent-hover); }
</style>
