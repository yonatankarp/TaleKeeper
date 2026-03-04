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

  const whisperModels = [
    { value: 'tiny', label: 'tiny', note: 'Fastest, lowest accuracy' },
    { value: 'base', label: 'base', note: 'Fast, low accuracy' },
    { value: 'small', label: 'small', note: 'Balanced speed/accuracy' },
    { value: 'medium', label: 'medium', note: 'Good accuracy, slower' },
    { value: 'distil-large-v3', label: 'distil-large-v3', note: 'Near-best accuracy, faster than large-v3 (Recommended)' },
    { value: 'large-v3', label: 'large-v3', note: 'Best accuracy, slowest' },
  ];

  async function load() {
    settings = await api.get<Record<string, string>>('/settings');
    if (!settings.whisper_model) settings.whisper_model = 'distil-large-v3';
    if (!settings.llm_base_url) settings.llm_base_url = '';
    if (!settings.llm_api_key) settings.llm_api_key = '';
    if (!settings.llm_model) settings.llm_model = '';
    if (!settings.image_model) settings.image_model = '';
    if (!settings.image_steps) settings.image_steps = '4';
    if (!settings.image_guidance_scale) settings.image_guidance_scale = '0';
    if (!settings.hf_token) settings.hf_token = '';
    if (!settings.whisper_batch_size) settings.whisper_batch_size = '';
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
        ? 'Image engine is available.'
        : `Error: ${status.message}`;
    } catch {
      imageResult = 'Image engine unavailable. Check your installation.';
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

  async function resetDefaults() {
    if (!confirm('Reset all settings to defaults? API keys and tokens will be preserved.')) return;
    await api.post('/settings/reset');
    await load();
    showToast('Settings reset to defaults');
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
          <option value={m.value}>{m.label} — {m.note}</option>
        {/each}
      </select>
    </label>
    <label>
      Batch Size
      <input type="number" min="1" max="32" bind:value={settings.whisper_batch_size} placeholder="Auto-detected based on hardware" />
    </label>
    <p class="hint">Number of audio segments to process in parallel. Leave empty for automatic detection based on your Apple Silicon chip. Higher values use more memory but process faster.</p>
  </div>

  <div class="section">
    <h3>Providers</h3>

    <div class="provider-group">
      <h4>HuggingFace</h4>
      <p class="hint" style="margin-bottom: 0.75rem;">Required for speaker diarization. Create a free account at <a href="https://huggingface.co" target="_blank" rel="noopener">huggingface.co</a>, then generate an access token under <a href="https://huggingface.co/settings/tokens" target="_blank" rel="noopener">Settings &gt; Access Tokens</a>. You must also accept the <a href="https://huggingface.co/pyannote/speaker-diarization-3.1" target="_blank" rel="noopener">pyannote model license</a> before using diarization.</p>
      <label>
        Access Token
        <input type="password" bind:value={settings.hf_token} placeholder="hf_..." />
      </label>
    </div>

    <div class="provider-group">
      <h4>LLM Provider</h4>
      <p class="hint" style="margin-bottom: 0.75rem;">Configure any OpenAI-compatible provider. Leave fields empty to use defaults (Ollama at localhost:11434).</p>
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
      <p class="hint">Recommended models: <strong>llama3.1:8b</strong> (fast, good quality), <strong>mistral:7b</strong> (fast), <strong>llama3.1:70b</strong> (best quality, needs 48GB+ RAM). Ollama is auto-detected for optimized settings.</p>
      <div class="action-row">
        <button class="btn" onclick={testLlm} disabled={testingLlm}>
          {testingLlm ? 'Testing...' : 'Test Connection'}
        </button>
        {#if llmResult}
          <span class="test-result">{llmResult}</span>
        {/if}
      </div>
    </div>
  </div>

  <div class="section">
    <h3>Image Generation</h3>
    <p class="hint" style="margin-bottom: 0.75rem;">Images are generated locally using mflux (MLX-native FLUX). No external server required.</p>
    <label>
      Model
      <input type="text" bind:value={settings.image_model} placeholder="FLUX.2-Klein-4B-Distilled" />
    </label>
    <p class="hint">Recommended: <strong>FLUX.2-Klein-4B-Distilled</strong> (fast, ~4GB). The model is downloaded automatically on first use.</p>
    <div class="settings-row">
      <label>
        Steps
        <input type="number" min="1" max="50" bind:value={settings.image_steps} placeholder="4" />
      </label>
      <label>
        Guidance Scale
        <input type="number" min="0" max="20" step="0.5" bind:value={settings.image_guidance_scale} placeholder="0" />
      </label>
    </div>
    <p class="hint">Lower steps = faster generation. Default: 4 steps, 0 guidance scale (best for Klein distilled model).</p>
    <div class="action-row">
      <button class="btn" onclick={testImage} disabled={testingImage}>
        {testingImage ? 'Checking...' : 'Check Availability'}
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
    <button class="btn btn-danger" onclick={resetDefaults}>Reset to Defaults</button>
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

  .provider-group {
    margin-bottom: 1.25rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid var(--border);
  }

  .provider-group:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
  }

  .provider-group h4 {
    margin: 0 0 0.25rem;
    font-size: 0.9rem;
  }

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

  .hint {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin: 0.25rem 0 0;
  }

  .hint a {
    color: var(--accent);
  }

  .hint strong {
    color: var(--text-secondary);
  }

  .action-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-top: 0.5rem;
  }

  .test-result { font-size: 0.85rem; color: var(--text-secondary); }

  .settings-row {
    display: flex;
    gap: 1rem;
  }

  .settings-row label {
    flex: 1;
  }

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
  .btn-danger { background: var(--danger); border-color: var(--danger); color: #fff; }
  .btn-danger:hover { opacity: 0.85; }
</style>
