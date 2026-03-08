<script lang="ts">
  type Props = { sessionId: number; onTimeUpdate?: (time: number) => void };
  let { sessionId, onTimeUpdate }: Props = $props();

  let audioEl: HTMLAudioElement | undefined = $state();

  export function seekTo(time: number) {
    if (audioEl) {
      audioEl.currentTime = time;
      audioEl.play();
    }
  }

  let audioUrl = $derived(`/api/sessions/${sessionId}/audio`);
</script>

<div class="audio-player">
  <audio bind:this={audioEl} controls src={audioUrl} preload="metadata"
    ontimeupdate={() => onTimeUpdate?.(audioEl?.currentTime ?? 0)}>
    <track kind="captions" />
  </audio>
</div>

<style>
  .audio-player {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  audio {
    width: 100%;
    outline: none;
  }
</style>
