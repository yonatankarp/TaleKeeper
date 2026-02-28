<script lang="ts">
  import { api } from '../lib/api';

  type Props = { onDismiss: () => void };
  let { onDismiss }: Props = $props();

  type SetupStatus = {
    is_first_run: boolean;
    data_dir_exists: boolean;
    ollama_running: boolean;
    ollama_models: string[];
  };

  let status = $state<SetupStatus | null>(null);
  let step = $state(0);

  async function load() {
    status = await api.get<SetupStatus>('/setup-status');
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
          <span class="icon">{status.data_dir_exists ? 'OK' : '--'}</span>
          <span>Data directory</span>
        </div>

        <div class="check" class:ok={status.ollama_running}>
          <span class="icon">{status.ollama_running ? 'OK' : '--'}</span>
          <div>
            <span>Ollama (for summaries)</span>
            {#if !status.ollama_running}
              <p class="hint">
                Install Ollama from <strong>ollama.com</strong>, then run:<br />
                <code>ollama serve</code><br />
                <code>ollama pull llama3.1:8b</code>
              </p>
            {:else if status.ollama_models.length === 0}
              <p class="hint">
                Ollama is running but no models found. Pull one:<br />
                <code>ollama pull llama3.1:8b</code>
              </p>
            {:else}
              <p class="hint">Models available: {status.ollama_models.join(', ')}</p>
            {/if}
          </div>
        </div>

        <div class="check ok">
          <span class="icon">OK</span>
          <span>Whisper (transcription) — will download on first use</span>
        </div>
      </div>

      <div class="actions">
        <button class="btn" onclick={load}>Re-check</button>
        <button class="btn btn-primary" onclick={onDismiss}>
          {status.ollama_running ? 'Get Started' : 'Continue Anyway'}
        </button>
      </div>

      {#if !status.ollama_running}
        <p class="note">Ollama is optional — recording and transcription work without it. You'll need it for summary generation.</p>
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

  .hint {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin: 0.25rem 0 0;
  }

  .hint code {
    background: var(--bg-hover);
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    font-size: 0.8rem;
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
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); }
</style>
