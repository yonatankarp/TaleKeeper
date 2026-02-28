<script lang="ts">
  import { api } from '../lib/api';

  type Props = { sessionId: number; campaignId: number; onUpdate: () => void };
  let { sessionId, campaignId, onUpdate }: Props = $props();

  type Speaker = { id: number; diarization_label: string; player_name: string | null; character_name: string | null };
  type RosterEntry = { id: number; player_name: string; character_name: string; is_active: number };

  let speakers = $state<Speaker[]>([]);
  let roster = $state<RosterEntry[]>([]);
  let editingId = $state<number | null>(null);
  let editPlayer = $state('');
  let editCharacter = $state('');

  async function load() {
    const [suggestionsResp, rosterResp] = await Promise.all([
      api.get<Speaker[]>(`/sessions/${sessionId}/speakers`),
      api.get<RosterEntry[]>(`/campaigns/${campaignId}/roster`),
    ]);
    speakers = suggestionsResp;
    roster = rosterResp.filter(r => r.is_active);
  }

  function startEdit(s: Speaker) {
    editingId = s.id;
    editPlayer = s.player_name ?? '';
    editCharacter = s.character_name ?? '';
  }

  async function saveEdit() {
    if (editingId === null) return;
    await api.put(`/speakers/${editingId}`, {
      player_name: editPlayer,
      character_name: editCharacter,
    });
    editingId = null;
    await load();
    onUpdate();
  }

  function selectFromRoster(entry: RosterEntry) {
    editPlayer = entry.player_name;
    editCharacter = entry.character_name;
  }

  function speakerDisplay(s: Speaker): string {
    if (s.character_name && s.player_name) return `${s.character_name} (${s.player_name})`;
    return s.diarization_label;
  }

  // Speaker color based on label hash
  const colors = ['#e94560', '#f0a500', '#2d6a4f', '#5e60ce', '#00b4d8', '#ff6b6b', '#48bfe3', '#72efdd'];
  function speakerColor(label: string): string {
    let hash = 0;
    for (const ch of label) hash = ((hash << 5) - hash) + ch.charCodeAt(0);
    return colors[Math.abs(hash) % colors.length];
  }

  $effect(() => { load(); });
</script>

<div class="speaker-panel">
  <h4>Speakers</h4>
  {#each speakers as s}
    <div class="speaker-row">
      {#if editingId === s.id}
        <div class="edit-form">
          <input type="text" placeholder="Player name" bind:value={editPlayer} />
          <input type="text" placeholder="Character name" bind:value={editCharacter} />
          {#if roster.length > 0}
            <div class="roster-suggestions">
              {#each roster as r}
                <button class="roster-btn" onclick={() => selectFromRoster(r)}>
                  {r.character_name} ({r.player_name})
                </button>
              {/each}
            </div>
          {/if}
          <div class="btn-group">
            <button class="btn btn-primary btn-sm" onclick={saveEdit}>Save</button>
            <button class="btn btn-sm" onclick={() => (editingId = null)}>Cancel</button>
          </div>
        </div>
      {:else}
        <button class="speaker-label-btn" onclick={() => startEdit(s)}>
          <span class="speaker-badge" style="background: {speakerColor(s.diarization_label)}">
            {speakerDisplay(s)}
          </span>
        </button>
      {/if}
    </div>
  {/each}

  {#if speakers.length === 0}
    <p class="empty">No speakers detected yet.</p>
  {/if}
</div>

<style>
  .speaker-panel {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  h4 { margin: 0 0 0.75rem; }

  .speaker-row { margin-bottom: 0.5rem; }

  .speaker-label-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
  }

  .speaker-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    color: #fff;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .edit-form {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .roster-suggestions {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
  }

  .roster-btn {
    padding: 0.2rem 0.5rem;
    font-size: 0.75rem;
    background: var(--bg-hover);
    border: 1px solid var(--btn-blue);
    border-radius: 12px;
    color: var(--text);
    cursor: pointer;
  }

  .roster-btn:hover { background: var(--btn-blue); }

  input {
    padding: 0.4rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
  }

  .btn {
    padding: 0.4rem 0.75rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-surface);
    color: var(--text);
    cursor: pointer;
    font-size: 0.8rem;
  }

  .btn:hover { background: var(--bg-hover); }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-sm { padding: 0.25rem 0.5rem; }
  .btn-group { display: flex; gap: 0.5rem; }

  .empty { color: var(--text-faint); font-size: 0.85rem; }
</style>
