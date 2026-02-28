<script lang="ts">
  import { api } from '../lib/api';

  type Props = { campaignId: number };
  let { campaignId }: Props = $props();

  type RosterEntry = { id: number; player_name: string; character_name: string; is_active: number };

  let entries = $state<RosterEntry[]>([]);
  let newPlayer = $state('');
  let newCharacter = $state('');
  let editingId = $state<number | null>(null);
  let editPlayer = $state('');
  let editCharacter = $state('');

  async function load() {
    entries = await api.get<RosterEntry[]>(`/campaigns/${campaignId}/roster`);
  }

  async function add() {
    if (!newPlayer.trim() || !newCharacter.trim()) return;
    await api.post(`/campaigns/${campaignId}/roster`, {
      player_name: newPlayer,
      character_name: newCharacter,
    });
    newPlayer = '';
    newCharacter = '';
    await load();
  }

  function startEdit(e: RosterEntry) {
    editingId = e.id;
    editPlayer = e.player_name;
    editCharacter = e.character_name;
  }

  async function saveEdit() {
    if (editingId === null) return;
    await api.put(`/roster/${editingId}`, {
      player_name: editPlayer,
      character_name: editCharacter,
    });
    editingId = null;
    await load();
  }

  async function toggleActive(e: RosterEntry) {
    await api.put(`/roster/${e.id}`, { is_active: !e.is_active });
    await load();
  }

  async function remove(id: number) {
    if (!confirm('Remove this roster entry?')) return;
    await api.del(`/roster/${id}`);
    await load();
  }

  $effect(() => { load(); });
</script>

<div class="page">
  <h2>Player Roster</h2>

  <div class="add-form card">
    <div class="form-row">
      <input type="text" placeholder="Player name" bind:value={newPlayer} />
      <input type="text" placeholder="Character name" bind:value={newCharacter} />
      <button class="btn btn-primary" onclick={add}>Add</button>
    </div>
  </div>

  <div class="roster-list">
    {#each entries as e}
      <div class="card roster-entry" class:inactive={!e.is_active}>
        {#if editingId === e.id}
          <div class="form-row">
            <input type="text" bind:value={editPlayer} />
            <input type="text" bind:value={editCharacter} />
            <button class="btn btn-primary btn-sm" onclick={saveEdit}>Save</button>
            <button class="btn btn-sm" onclick={() => (editingId = null)}>Cancel</button>
          </div>
        {:else}
          <div class="entry-info">
            <strong>{e.character_name}</strong>
            <span class="player-label">({e.player_name})</span>
            {#if !e.is_active}<span class="inactive-badge">Inactive</span>{/if}
          </div>
          <div class="btn-group">
            <button class="btn btn-sm" onclick={() => toggleActive(e)}>
              {e.is_active ? 'Deactivate' : 'Activate'}
            </button>
            <button class="btn btn-sm" onclick={() => startEdit(e)}>Edit</button>
            <button class="btn btn-sm btn-danger" onclick={() => remove(e.id)}>Remove</button>
          </div>
        {/if}
      </div>
    {/each}
  </div>

  {#if entries.length === 0}
    <p class="empty">No players in the roster yet.</p>
  {/if}
</div>

<style>
  .add-form { margin-bottom: 1.5rem; }

  .form-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .roster-list { display: flex; flex-direction: column; gap: 0.5rem; }

  .roster-entry {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem 1rem;
  }

  .roster-entry.inactive { opacity: 0.5; }

  .entry-info { display: flex; align-items: center; gap: 0.5rem; }
  .player-label { color: var(--text-muted); }
  .inactive-badge {
    font-size: 0.7rem;
    background: var(--badge-dark);
    color: var(--text-muted);
    padding: 0.15rem 0.4rem;
    border-radius: 8px;
  }

  .card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }

  input {
    padding: 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
  }

  .btn {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-surface);
    color: var(--text);
    cursor: pointer;
    font-size: 0.85rem;
    white-space: nowrap;
  }

  .btn:hover { background: var(--bg-hover); }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); }
  .btn-danger { color: var(--accent); }
  .btn-sm { padding: 0.25rem 0.75rem; font-size: 0.8rem; }
  .btn-group { display: flex; gap: 0.5rem; }

  .empty { text-align: center; color: var(--text-muted); margin-top: 2rem; }
</style>
