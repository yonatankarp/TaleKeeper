<script lang="ts">
  import { api, generateImageStream, type ImageMeta } from '../lib/api';
  import ConfirmDialog from './ConfirmDialog.svelte';
  import Spinner from './Spinner.svelte';

  type Props = { sessionId: number };
  let { sessionId }: Props = $props();

  let images = $state<ImageMeta[]>([]);
  let generating = $state(false);
  let craftingScene = $state(false);
  let genPhase = $state<string | null>(null);
  let error = $state<string | null>(null);
  let imageProviderOk = $state<boolean | null>(null);
  let imageProviderMsg = $state('');
  let promptText = $state('');
  let confirmDeleteId = $state<number | null>(null);
  let genElapsed = $state(0);
  let genTimer: ReturnType<typeof setInterval> | null = null;
  let cancelStream: (() => void) | null = null;

  const phaseLabels: Record<string, string> = {
    crafting_scene: 'Crafting scene...',
    generating_image: 'Generating image...',
  };

  function startGenTimer() {
    genElapsed = 0;
    genTimer = setInterval(() => { genElapsed += 1; }, 1000);
  }

  function stopGenTimer() {
    if (genTimer) { clearInterval(genTimer); genTimer = null; }
  }

  async function load() {
    images = await api.get<ImageMeta[]>(`/sessions/${sessionId}/images`);
  }

  async function checkImageProvider() {
    try {
      const status = await api.get<{ status: string; message?: string }>('/settings/image-health');
      imageProviderOk = status.status === 'ok';
      imageProviderMsg = status.message ?? '';
    } catch {
      imageProviderOk = false;
      imageProviderMsg = 'Cannot reach image provider';
    }
  }

  async function craftScene() {
    craftingScene = true;
    error = null;
    try {
      const result = await api.post<{ scene_description: string }>(`/sessions/${sessionId}/craft-scene`);
      promptText = result.scene_description;
    } catch (e: any) {
      error = e.message;
    } finally {
      craftingScene = false;
    }
  }

  function generateImage() {
    const prompt = promptText.trim() || null;
    generating = true;
    genPhase = null;
    error = null;
    startGenTimer();

    const handle = generateImageStream(
      sessionId,
      prompt,
      (phase) => { genPhase = phase; },
      (_image) => {
        generating = false;
        genPhase = null;
        stopGenTimer();
        cancelStream = null;
        promptText = '';
        load();
      },
      (message) => {
        generating = false;
        genPhase = null;
        stopGenTimer();
        cancelStream = null;
        error = message;
      },
    );
    cancelStream = handle.cancel;
  }

  async function deleteImage(id: number) {
    await api.del(`/images/${id}`);
    confirmDeleteId = null;
    await load();
  }

  $effect(() => { load(); checkImageProvider(); });
</script>

<div class="illustrations-section">
  {#if error}
    <div class="error">{error}</div>
  {/if}

  {#if imageProviderOk === false}
    <div class="warning">
      <strong>Image provider not available</strong>
      <p>{imageProviderMsg || 'No image provider is reachable. Check the base URL and API key in Settings.'}</p>
    </div>
  {/if}

  <div class="prompt-area">
    <div class="actions">
      <button class="btn btn-primary" onclick={craftScene} disabled={craftingScene || generating}>
        {#if craftingScene}
          <Spinner size="14px" /> Crafting scene...
        {:else}
          Generate Scene
        {/if}
      </button>
    </div>

    <textarea
      class="prompt-input"
      bind:value={promptText}
      placeholder="Scene description will appear here after clicking Generate Scene, or type your own prompt directly..."
      disabled={generating}
      rows="4"
    ></textarea>

    <button class="btn btn-primary" onclick={generateImage} disabled={generating || imageProviderOk === false}>
      {#if generating}
        <Spinner size="14px" /> {phaseLabels[genPhase ?? ''] ?? 'Starting...'} ({genElapsed}s)
      {:else}
        Generate Image
      {/if}
    </button>
  </div>

  <div class="gen-hint">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
    Click "Generate Scene" to craft an image prompt from the session, or type your own. Image generation may take a minute or more depending on your hardware.
  </div>

  {#if images.length > 0}
    <h3>Generated Images</h3>
    <div class="image-list">
      {#each images as img}
        <div class="image-card">
          <img src="/api/images/{img.id}/file" alt="Generated scene" class="image-preview" />
          <div class="image-details">
            <p class="image-prompt">{img.prompt}</p>
            <div class="image-meta">
              <span>Model: {img.model_used}</span>
              <span>Generated: {img.generated_at}</span>
            </div>
            <div class="btn-group">
              <button class="btn btn-sm btn-danger" onclick={() => (confirmDeleteId = img.id)}>Delete</button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if images.length === 0 && !generating}
    <p class="empty">No illustrations generated yet. Generate a scene after your session is transcribed or summarized.</p>
  {/if}
</div>

{#if confirmDeleteId !== null}
  <ConfirmDialog
    title="Delete Image"
    message="Are you sure you want to delete this image? This cannot be undone."
    confirmLabel="Delete"
    onconfirm={() => deleteImage(confirmDeleteId!)}
    oncancel={() => (confirmDeleteId = null)}
  />
{/if}

<style>
  .illustrations-section {
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

  .warning p { margin: 0.25rem 0 0; }

  .prompt-area {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .actions {
    display: flex;
    gap: 0.75rem;
  }

  .prompt-input {
    width: 100%;
    padding: 0.75rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.9rem;
    resize: vertical;
    box-sizing: border-box;
  }

  .prompt-input:disabled { opacity: 0.5; }

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

  .gen-hint svg { flex-shrink: 0; }

  .image-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .image-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }

  .image-preview {
    width: 100%;
    max-height: 400px;
    object-fit: contain;
    background: var(--bg-input);
    display: block;
  }

  .image-details {
    padding: 1rem;
  }

  .image-prompt {
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 0 0 0.5rem;
    white-space: pre-wrap;
  }

  .image-meta {
    display: flex;
    gap: 1rem;
    font-size: 0.75rem;
    color: var(--text-faint);
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

  .empty { color: var(--text-faint); text-align: center; padding: 2rem; }
</style>
