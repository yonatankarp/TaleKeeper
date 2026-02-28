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
  let searchQuery = $state('');
  let chunkProgress = $state<{ chunk: number; total: number } | null>(null);

  $effect(() => { retranscribeLang = language; });

  let filteredSegments = $derived(() => {
    if (!searchQuery.trim()) return segments;
    const q = searchQuery.toLowerCase();
    return segments.filter(seg =>
      seg.text.toLowerCase().includes(q) ||
      speakerLabel(seg).toLowerCase().includes(q)
    );
  });

  async function load() {
    segments = await api.get<Segment[]>(`/sessions/${sessionId}/transcript`);
  }

  async function retranscribe() {
    transcribing = true;
    error = null;
    chunkProgress = null;
    segments = [];

    try {
      const res = await fetch(`/api/sessions/${sessionId}/retranscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: retranscribeLang }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(typeof err.detail === 'string' ? err.detail : res.statusText);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last partial line in the buffer
        buffer = lines.pop() ?? '';

        let currentEvent = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ') && currentEvent) {
            const data = JSON.parse(line.slice(6));

            if (currentEvent === 'segment') {
              segments = [...segments, {
                id: Date.now() + segments.length,
                text: data.text,
                start_time: data.start_time,
                end_time: data.end_time,
                speaker_id: null,
                diarization_label: null,
                player_name: null,
                character_name: null,
              }];
              requestAnimationFrame(() => {
                if (container) container.scrollTop = container.scrollHeight;
              });
            } else if (currentEvent === 'progress') {
              chunkProgress = { chunk: data.chunk, total: data.total_chunks };
            } else if (currentEvent === 'done') {
              chunkProgress = null;
            } else if (currentEvent === 'error') {
              error = data.message || 'Transcription failed';
            }
            currentEvent = '';
          } else if (line.trim() === '') {
            currentEvent = '';
          }
        }
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Transcription failed';
    } finally {
      transcribing = false;
      chunkProgress = null;
      // Reload to get speaker-populated segments from DB
      await load();
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
    if (seg.character_name) return seg.character_name;
    if (seg.player_name) return seg.player_name;
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
    {#if transcribing && chunkProgress}
      <span class="chunk-progress">Chunk {chunkProgress.chunk} of {chunkProgress.total}</span>
    {/if}
  </div>
{/if}

{#if segments.length > 0}
  <div class="search-bar">
    <input
      type="text"
      placeholder="Search transcript..."
      bind:value={searchQuery}
    />
    {#if searchQuery.trim()}
      <span class="match-count">{filteredSegments().length} matches</span>
      <button class="clear-btn" onclick={() => (searchQuery = '')}>Clear</button>
    {/if}
  </div>
{/if}

<div class="transcript-container" bind:this={container}>
  {#if transcribing && segments.length === 0 && !chunkProgress}
    <p class="empty">Transcribing audio…</p>
  {:else if transcribing && segments.length === 0 && chunkProgress}
    <p class="empty">Transcribing chunk {chunkProgress.chunk} of {chunkProgress.total}…</p>
  {:else if segments.length === 0}
    <p class="empty">
      {isRecording ? 'Waiting for speech...' : 'No transcript available. Start recording or retranscribe audio to generate one.'}
    </p>
  {:else if filteredSegments().length === 0}
    <p class="empty">No matches found.</p>
  {:else}
    {#each filteredSegments() as seg}
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
  .search-bar {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .search-bar input {
    flex: 1;
    padding: 0.4rem 0.75rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.85rem;
    box-sizing: border-box;
  }

  .match-count {
    font-size: 0.8rem;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .clear-btn {
    padding: 0.3rem 0.6rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    cursor: pointer;
    font-size: 0.8rem;
    white-space: nowrap;
  }

  .clear-btn:hover { background: var(--bg-hover); }

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

  .chunk-progress {
    font-size: 0.8rem;
    color: var(--text-muted);
    white-space: nowrap;
  }
</style>
