<script lang="ts">
  import { api } from '../lib/api';
  import LanguageSelect from './LanguageSelect.svelte';

  type Props = {
    sessionId: number;
    isRecording?: boolean;
    hasAudio?: boolean;
    language?: string;
    onSegmentClick?: (startTime: number) => void;
  };
  let { sessionId, isRecording = false, hasAudio = false, language = 'en', onSegmentClick }: Props = $props();

  type Segment = {
    id: number;
    text: string;
    start_time: number;
    end_time: number;
    speaker_id: number | null;
    diarization_label: string | null;
    player_name: string | null;
    character_name: string | null;
  };

  let segments = $state<Segment[]>([]);
  let container: HTMLDivElement | undefined = $state();
  let transcribing = $state(false);
  let error = $state<string | null>(null);
  let retranscribeLang = $state('en');

  $effect(() => { retranscribeLang = language; });

  async function load() {
    segments = await api.get<Segment[]>(`/sessions/${sessionId}/transcript`);
  }

  async function retranscribe() {
    transcribing = true;
    error = null;
    try {
      await api.post(`/sessions/${sessionId}/retranscribe`, { language: retranscribeLang });
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Transcription failed';
    } finally {
      transcribing = false;
    }
  }

  // Listen for live transcript segments via WebSocket messages
  // The RecordingControls component sends transcript messages
  export function addLiveSegment(seg: { text: string; start_time: number; end_time: number }) {
    segments = [...segments, {
      id: Date.now(),
      text: seg.text,
      start_time: seg.start_time,
      end_time: seg.end_time,
      speaker_id: null,
      diarization_label: null,
      player_name: null,
      character_name: null,
    }];
    // Auto-scroll to bottom
    requestAnimationFrame(() => {
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    });
  }

  function formatTime(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return [h, m, s].map((v) => String(v).padStart(2, '0')).join(':');
  }

  function speakerLabel(seg: Segment): string {
    if (seg.character_name && seg.player_name) {
      return `${seg.character_name} (${seg.player_name})`;
    }
    if (seg.diarization_label) return seg.diarization_label;
    return '';
  }

  $effect(() => { load(); });
</script>

{#if error}
  <p class="error">{error}</p>
{/if}

{#if hasAudio && !isRecording}
  <div class="retranscribe-bar">
    <LanguageSelect compact value={retranscribeLang} onchange={(code) => (retranscribeLang = code)} />
    <button class="retranscribe-btn" onclick={retranscribe} disabled={transcribing}>
      {transcribing ? 'Transcribing…' : 'Retranscribe'}
    </button>
  </div>
{/if}

<div class="transcript-container" bind:this={container}>
  {#if transcribing}
    <p class="empty">Transcribing audio… this may take a while.</p>
  {:else if segments.length === 0}
    <p class="empty">
      {isRecording ? 'Waiting for speech...' : 'No transcript available.'}
    </p>
  {:else}
    {#each segments as seg}
      <button
        class="segment"
        onclick={() => onSegmentClick?.(seg.start_time)}
      >
        <span class="timestamp">{formatTime(seg.start_time)}</span>
        {#if speakerLabel(seg)}
          <span class="speaker">{speakerLabel(seg)}</span>
        {/if}
        <span class="text">{seg.text}</span>
      </button>
    {/each}
  {/if}
</div>

<style>
  .transcript-container {
    max-height: 500px;
    overflow-y: auto;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.5rem;
  }

  .segment {
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    width: 100%;
    background: none;
    border: none;
    color: inherit;
    font: inherit;
    text-align: left;
  }

  .segment:hover {
    background: var(--bg-hover);
  }

  .timestamp {
    color: var(--text-faint);
    font-family: 'SF Mono', monospace;
    font-size: 0.8rem;
    flex-shrink: 0;
    padding-top: 0.1rem;
  }

  .speaker {
    color: var(--accent);
    font-weight: 600;
    font-size: 0.85rem;
    flex-shrink: 0;
  }

  .text {
    color: var(--text);
    font-size: 0.9rem;
  }

  .empty {
    text-align: center;
    color: var(--text-faint);
    padding: 2rem;
  }

  .error {
    color: var(--danger, #e53e3e);
    background: var(--danger-bg, #fff5f5);
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
  }

  .retranscribe-bar {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .retranscribe-btn {
    padding: 0.4rem 1rem;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    background: var(--accent);
    color: white;
    white-space: nowrap;
  }

  .retranscribe-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .retranscribe-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
