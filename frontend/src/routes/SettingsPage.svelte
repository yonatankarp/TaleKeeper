<script lang="ts">
  import { api } from '../lib/api';
  import Spinner from '../components/Spinner.svelte';
  import { wizard } from '../lib/wizard.svelte';

  let settings = $state<Record<string, string>>({});
  let pageLoading = $state(true);
  let toast = $state<string | null>(null);
  let testingLlm = $state(false);
  let llmResult = $state<string | null>(null);
  let testingImage = $state(false);
  let imageResult = $state<string | null>(null);

  const whisperModels = ['tiny', 'base', 'small', 'medium', 'large-v3'];

  async function load() {
    settings = await api.get<Record<string, string>>('/settings');
    if (!settings.whisper_model) settings.whisper_model = 'medium';
    if (!settings.llm_base_url) settings.llm_base_url = '';
    if (!settings.llm_api_key) settings.llm_api_key = '';
    if (!settings.llm_model) settings.llm_model = '';
    if (!settings.image_base_url) settings.image_base_url = '';
    if (!settings.image_api_key) settings.image_api_key = '';
    if (!settings.image_model) settings.image_model = '';
    if (!settings.live_transcription) settings.live_transcription = 'false';
    if (!settings.data_dir) settings.data_dir = '';
    pageLoading = false;
  }

  async function save() {
    await api.put('/settings', { settings });
    showToast('Settings saved');
  }

  async function testLlm() {
    testingLlm = true;
    try {
      const status = await api.get<{ status: string; message?: string }>('/llm/status');
      llmResult = status.status === 'ok'
        ? 'Connected! LLM provider is reachable.'
        : `Error: ${status.message}`;
    } catch {
      llmResult = 'Cannot reach LLM provider. Check your settings.';
    } finally {
      testingLlm = false;
    }
  }

  async function testImage() {
    testingImage = true;
    try {
      const status = await api.get<{ status: string; message?: string }>('/settings/image-health');
      imageResult = status.status === 'ok'
        ? 'Connected! Image provider is reachable.'
        : `Error: ${status.message}`;
    } catch {
      imageResult = 'Cannot reach image provider. Check your settings.';
    } finally {
      testingImage = false;
    }
  }

  function showToast(msg: string) {
    toast = msg;
    setTimeout(() => { toast = null; }, 3000);
  }

  async function browseDataDir() {
    const result = await api.post<{ path: string | null }>('/pick-directory');
    if (result.path) settings.data_dir = result.path;
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
    <h3>LLM Provider</h3>
    <p class="hint" style="margin-bottom: 0.75rem;">Configure any OpenAI-compatible provider. Leave fields empty to use defaults (Ollama at localhost:11434, model llama3.1:8b).</p>
    <label>
      Base URL
      <input type="text" bind:value={settings.llm_base_url} placeholder="http://localhost:11434/v1" />
    </label>
    <label>
      API Key
      <input type="password" bind:value={settings.llm_api_key} placeholder="Not required for local providers" />
    </label>
    <label>
      Model
      <input type="text" bind:value={settings.llm_model} placeholder="llama3.1:8b" />
    </label>
    <div class="action-row">
      <button class="btn" onclick={testLlm} disabled={testingLlm}>
        {testingLlm ? 'Testing...' : 'Test Connection'}
      </button>
      {#if llmResult}
        <span class="test-result">{llmResult}</span>
      {/if}
    </div>
  </div>

  <div class="section">
    <h3>Image Generation</h3>
    <p class="hint" style="margin-bottom: 0.75rem;">Configure an OpenAI-compatible image generation provider. Leave fields empty to use defaults (Ollama at localhost:11434, model x/flux2-klein:9b). You can also use cloud providers like OpenAI (dall-e-3).</p>
    <label>
      Base URL
      <input type="text" bind:value={settings.image_base_url} placeholder="http://localhost:11434/v1" />
    </label>
    <label>
      API Key
      <input type="password" bind:value={settings.image_api_key} placeholder="Not required for local providers" />
    </label>
    <label>
      Model
      <input type="text" bind:value={settings.image_model} placeholder="x/flux2-klein:9b" />
    </label>
    <div class="action-row">
      <button class="btn" onclick={testImage} disabled={testingImage}>
        {testingImage ? 'Testing...' : 'Test Connection'}
      </button>
      {#if imageResult}
        <span class="test-result">{imageResult}</span>
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
    <label>
      Data directory
      <div class="input-with-browse">
        <input type="text" bind:value={settings.data_dir} placeholder="data (default)" />
        <button class="btn btn-browse" type="button" onclick={browseDataDir}>Browse</button>
      </div>
    </label>
    <p class="hint">Where session recordings, transcripts, and summaries are stored. Leave blank for the default (<code>data</code>). Back up this folder to preserve your data.</p>
  </div>

  <div class="bottom-actions">
    <button class="btn btn-primary" onclick={save}>Save Settings</button>
    <button class="btn" onclick={() => wizard.show()}>Run Setup Wizard</button>
  </div>
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

  .input-with-browse {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .input-with-browse input { flex: 1; }

  .btn-browse {
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
    white-space: nowrap;
    flex-shrink: 0;
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

  .bottom-actions {
    display: flex;
    gap: 0.75rem;
    align-items: center;
  }

  .btn:hover { background: var(--bg-hover); }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); }
</style>
