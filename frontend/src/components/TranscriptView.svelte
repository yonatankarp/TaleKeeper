<script lang="ts">
  import { api } from '../lib/api';
  import LanguageSelect from './LanguageSelect.svelte';

  type Props = {
    sessionId: number;
    campaignId?: number;
    isRecording?: boolean;
    hasAudio?: boolean;
    language?: string;
    status?: string;
    onSegmentClick?: (startTime: number) => void;
  };
  let { sessionId, campaignId, isRecording = false, hasAudio = false, language = 'en', status, onSegmentClick }: Props = $props();

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
  let retranscribeNumSpeakers = $state(5);
  let searchQuery = $state('');
  let chunkProgress = $state<{ chunk: number; total: number } | null>(null);
  let copiedId = $state<number | null>(null);

  $effect(() => { retranscribeLang = language; });

  $effect(() => {
    if (campaignId) {
      api.get<{ num_speakers: number }>(`/campaigns/${campaignId}`).then(c => {
        retranscribeNumSpeakers = c.num_speakers;
      });
    }
  });

  let filteredSegments = $derived(() => {
    if (!searchQuery.trim()) return segments;
    const q = searchQuery.toLowerCase();
    return segments.filter(seg =>
      seg.text.toLowerCase().includes(q) ||
      speakerLabel(seg).toLowerCase().includes(q)
    );
  });

  export async function load() {
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
        body: JSON.stringify({ language: retranscribeLang, num_speakers: retranscribeNumSpeakers }),
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

  async function copyLine(seg: Segment) {
    const label = speakerLabel(seg);
    const line = label ? `[${formatTime(seg.start_time)}] ${label}: ${seg.text}` : `[${formatTime(seg.start_time)}] ${seg.text}`;
    await navigator.clipboard.writeText(line);
    copiedId = seg.id;
    setTimeout(() => { if (copiedId === seg.id) copiedId = null; }, 1500);
  }

  function downloadTranscript() {
    const lines = segments.map(seg => {
      const label = speakerLabel(seg);
      return label
        ? `[${formatTime(seg.start_time)}] ${label}: ${seg.text}`
        : `[${formatTime(seg.start_time)}] ${seg.text}`;
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript-session-${sessionId}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  $effect(() => { load(); });
</script>

{#if error}
  <p class="error">{error}</p>
{/if}

{#if (status === 'audio_ready' || status === 'transcribing') && !transcribing}
  <div class="processing-banner">
    <span class="processing-dot"></span>
    {status === 'audio_ready' ? 'Preparing audio for transcription...' : 'Processing audio — transcribing and identifying speakers...'}
  </div>
{/if}

{#if hasAudio && !isRecording && status !== 'transcribing' && status !== 'audio_ready'}
  <div class="retranscribe-bar">
    <LanguageSelect compact value={retranscribeLang} onchange={(code) => (retranscribeLang = code)} />
    <label class="speakers-label">Speakers
      <input type="number" min="1" max="10" bind:value={retranscribeNumSpeakers} class="speakers-input" />
    </label>
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
    <button class="download-btn" onclick={downloadTranscript} title="Download transcript">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
    </button>
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
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <div
        class="segment"
        class:clickable={hasAudio}
        onclick={() => onSegmentClick?.(seg.start_time)}
        role={hasAudio ? 'button' : undefined}
        tabindex={hasAudio ? 0 : undefined}
        onkeydown={(e: KeyboardEvent) => { if (hasAudio && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); onSegmentClick?.(seg.start_time); } }}
      >
        <span class="timestamp">{formatTime(seg.start_time)}</span>
        {#if speakerLabel(seg)}
          <span class="speaker">{speakerLabel(seg)}</span>
        {/if}
        <span class="text">{seg.text}</span>
        <button
          class="copy-btn"
          title="Copy line"
          onclick={(e: MouseEvent) => { e.stopPropagation(); copyLine(seg); }}
        >
          {#if copiedId === seg.id}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          {:else}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
          {/if}
        </button>
      </div>
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

  .download-btn {
    padding: 0.3rem 0.5rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    cursor: pointer;
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .download-btn:hover { background: var(--bg-hover); }

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
    user-select: text;
    align-items: flex-start;
  }

  .segment:hover {
    background: var(--bg-hover);
  }

  .segment.clickable {
    cursor: pointer;
  }

  .segment:hover .copy-btn {
    opacity: 1;
  }

  .timestamp {
    color: var(--text-faint);
    font-family: 'SF Mono', monospace;
    font-size: 0.8rem;
    flex-shrink: 0;
    padding-top: 0.1rem;
  }

  .segment.clickable:hover .timestamp {
    color: var(--accent);
  }

  .copy-btn {
    opacity: 0;
    background: none;
    border: none;
    color: var(--text-faint);
    cursor: pointer;
    padding: 0.15rem;
    flex-shrink: 0;
    border-radius: 3px;
    display: flex;
    align-items: center;
    margin-left: auto;
    transition: opacity 0.15s;
  }

  .copy-btn:hover {
    color: var(--accent);
    background: var(--bg-input);
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

  .processing-banner {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.6rem 1rem;
    background: var(--bg-surface);
    border: 1px solid var(--accent);
    border-radius: 6px;
    margin-bottom: 0.5rem;
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .processing-dot {
    width: 8px;
    height: 8px;
    background: var(--accent);
    border-radius: 50%;
    flex-shrink: 0;
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
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

  .speakers-label {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .speakers-input {
    width: 3.5rem;
    padding: 0.3rem 0.4rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-size: 0.85rem;
    text-align: center;
  }
</style>
