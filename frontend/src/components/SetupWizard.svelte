<script lang="ts">
  import { api } from '../lib/api';
  import Spinner from './Spinner.svelte';

  type Props = { onDismiss: () => void };
  let { onDismiss }: Props = $props();

  type SetupStatus = {
    is_first_run: boolean;
    data_dir_exists: boolean;
    llm_connected: boolean;
    data_dir: string;
  };

  let status = $state<SetupStatus | null>(null);
  let showDataInfo = $state(false);
  let showLlmInfo = $state(false);
  let checking = $state(false);

  let llmBaseUrl = $state('');
  let llmApiKey = $state('');
  let llmModel = $state('');
  let dataDir = $state('');

  async function load() {
    status = await api.get<SetupStatus>('/setup-status');
    const settings = await api.get<Record<string, string>>('/settings');
    llmBaseUrl = settings.llm_base_url || '';
    llmApiKey = settings.llm_api_key || '';
    llmModel = settings.llm_model || '';
    dataDir = settings.data_dir || '';
  }

  async function saveAndRecheck() {
    checking = true;
    try {
      await api.put('/settings', {
        settings: {
          llm_base_url: llmBaseUrl,
          llm_api_key: llmApiKey,
          llm_model: llmModel,
          data_dir: dataDir,
        },
      });
      status = await api.get<SetupStatus>('/setup-status');
    } finally {
      checking = false;
    }
  }

  async function dismiss() {
    await api.put('/settings', { settings: { setup_dismissed: 'true' } });
    onDismiss();
  }

  async function browseDataDir() {
    const result = await api.post<{ path: string | null }>('/pick-directory');
    if (result.path) dataDir = result.path;
  }

  $effect(() => { load(); });
</script>

<div class="wizard-overlay">
  <div class="wizard">
    <h2>Welcome to TaleKeeper</h2>
    <p>Let's make sure everything is set up for your D&D sessions.</p>

    {#if status}
      <div class="checks">
        <div class="check" class:ok={status.data_dir_exists}>
          <span class="icon">{status.data_dir_exists ? '\u2713' : '\u2717'}</span>
          <div class="data-section">
            <span>
              Data directory
              <button class="info-btn" onclick={() => (showDataInfo = !showDataInfo)} title="What is this?">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
              </button>
            </span>
            {#if showDataInfo}
              <div class="info-tooltip">
                <p>Your session recordings, transcripts, and summaries are all saved here. As long as this folder exists, your data is safe and will persist between sessions.</p>
              </div>
            {/if}
            <div class="data-dir-config">
              <label>
                Path
                <div class="input-with-browse">
                  <input type="text" bind:value={dataDir} placeholder={status.data_dir} />
                  <button class="btn btn-browse" type="button" onclick={browseDataDir}>Browse</button>
                </div>
              </label>
              <span class="resolved-path">Current: <code>{status.data_dir}</code></span>
            </div>
          </div>
        </div>

        <div class="check" class:ok={status.llm_connected}>
          <span class="icon">{status.llm_connected ? '\u2713' : '\u2717'}</span>
          <div class="llm-section">
            <span>
              LLM Provider (for summaries)
              <button class="info-btn" onclick={() => (showLlmInfo = !showLlmInfo)} title="What is this?">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
              </button>
            </span>
            {#if showLlmInfo}
              <div class="info-tooltip">
                <p><strong>Easiest local setup — Ollama (free):</strong></p>
                <ol>
                  <li>Install from <strong>ollama.com</strong></li>
                  <li>Run <code>ollama serve</code></li>
                  <li>Pull a model: <code>ollama pull llama3.1:8b</code></li>
                </ol>
                <p>Cloud providers (OpenAI, Groq, Together.ai, etc.) work too — just enter their URL and API key below.</p>
              </div>
            {/if}

            <div class="llm-config">
              <label>
                Base URL
                <input type="text" bind:value={llmBaseUrl} placeholder="http://localhost:11434/v1" />
              </label>
              <label>
                API Key
                <input type="password" bind:value={llmApiKey} placeholder="Not required for local providers" />
              </label>
              <label>
                Model
                <input type="text" bind:value={llmModel} placeholder="llama3.1:8b" />
              </label>
            </div>
          </div>
        </div>
      </div>

      <div class="actions">
        <button class="btn" onclick={saveAndRecheck} disabled={checking}>
          {#if checking}<Spinner size="14px" /> Checking...{:else}Re-check{/if}
        </button>
        <button class="btn btn-primary" onclick={dismiss}>
          {status.llm_connected ? 'Get Started' : 'Continue Anyway'}
        </button>
      </div>

      {#if !status.llm_connected}
        <p class="note">An LLM provider is optional — recording and transcription work without it. You'll need one for summary generation.</p>
      {/if}
    {:else}
      <p>Checking setup...</p>
    {/if}
  </div>
</div>

<style>
  .wizard-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }

  .wizard {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2rem;
    max-width: 500px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
  }

  .wizard h2 { margin: 0 0 0.5rem; color: var(--accent); }
  .wizard p { margin: 0.5rem 0; }

  .checks {
    margin: 1.5rem 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .check {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
    padding: 0.5rem;
    border-radius: 4px;
    background: var(--bg-input);
  }

  .icon {
    width: 24px;
    text-align: center;
    font-weight: bold;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .check.ok .icon { color: var(--success); }
  .check:not(.ok) .icon { color: var(--danger); }

  .data-section { flex: 1; min-width: 0; }
  .llm-section { flex: 1; min-width: 0; }

  .info-btn {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0;
    vertical-align: middle;
    margin-left: 0.25rem;
  }

  .info-btn:hover { color: var(--accent); }

  .info-tooltip {
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.75rem;
    margin-top: 0.5rem;
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .info-tooltip p { margin: 0.25rem 0; }

  .info-tooltip ol {
    margin: 0.25rem 0;
    padding-left: 1.25rem;
  }

  .info-tooltip li { margin: 0.15rem 0; }

  .info-tooltip code {
    background: var(--bg-input);
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    font-size: 0.8rem;
  }

  .data-dir-config {
    margin-top: 0.5rem;
  }

  .data-dir-config label {
    display: block;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
  }

  .data-dir-config input {
    display: block;
    width: 100%;
    padding: 0.35rem 0.5rem;
    margin-top: 0.15rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.8rem;
    box-sizing: border-box;
  }

  .input-with-browse {
    display: flex;
    gap: 0.35rem;
    align-items: center;
  }

  .input-with-browse input { flex: 1; }

  .btn-browse {
    padding: 0.35rem 0.6rem;
    font-size: 0.75rem;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .resolved-path {
    font-size: 0.75rem;
    color: var(--text-faint);
  }

  .resolved-path code {
    background: var(--bg-input);
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
  }

  .llm-config {
    margin-top: 0.5rem;
  }

  .llm-config label {
    display: block;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
  }

  .llm-config input {
    display: block;
    width: 100%;
    padding: 0.35rem 0.5rem;
    margin-top: 0.15rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.8rem;
    box-sizing: border-box;
  }


  .actions {
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
  }

  .note {
    font-size: 0.8rem;
    color: var(--text-faint);
    margin-top: 1rem;
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
