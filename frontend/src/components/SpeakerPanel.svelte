<script lang="ts">
  import { api } from '../lib/api';

  type Props = { sessionId: number; campaignId: number; hasAudio: boolean; onUpdate: () => void };
  let { sessionId, campaignId, hasAudio, onUpdate }: Props = $props();

  type Speaker = { id: number; diarization_label: string; player_name: string | null; character_name: string | null };
  type RosterEntry = { id: number; player_name: string; character_name: string; is_active: number };
  type VoiceSignature = { id: number; roster_entry_id: number; player_name: string; character_name: string; num_samples: number };

  let speakers = $state<Speaker[]>([]);
  let roster = $state<RosterEntry[]>([]);
  let signatures = $state<VoiceSignature[]>([]);
  let collapsed = $state(true);
  let editing = $state(false);
  let saving = $state(false);
  let generating = $state(false);
  let generateResult = $state<string | null>(null);
  let error = $state<string | null>(null);

  // Batch edit state: maps speaker id to { player_name, character_name }
  let edits = $state<Record<number, { player_name: string; character_name: string }>>({});

  // Set of roster_entry_ids that have signatures
  let signatureRosterIds = $derived(new Set(signatures.map(s => s.roster_entry_id)));

  // Check if any speaker is linked to a roster entry (for showing the generate button)
  let hasRosterLinkedSpeaker = $derived(
    speakers.some(s => s.player_name && s.character_name &&
      roster.some(r => r.player_name === s.player_name && r.character_name === s.character_name))
  );

  // Check if a speaker has a voice signature via roster match
  function hasSignature(s: Speaker): boolean {
    if (!s.player_name || !s.character_name) return false;
    const entry = roster.find(r => r.player_name === s.player_name && r.character_name === s.character_name);
    return entry ? signatureRosterIds.has(entry.id) : false;
  }

  async function load() {
    const [suggestionsResp, rosterResp, sigResp] = await Promise.all([
      api.get<Speaker[]>(`/sessions/${sessionId}/speakers`),
      api.get<RosterEntry[]>(`/campaigns/${campaignId}/roster`),
      api.get<VoiceSignature[]>(`/campaigns/${campaignId}/voice-signatures`),
    ]);
    speakers = suggestionsResp;
    roster = rosterResp.filter(r => r.is_active);
    signatures = sigResp;
  }

  function startBatchEdit() {
    const map: Record<number, { player_name: string; character_name: string }> = {};
    for (const s of speakers) {
      map[s.id] = { player_name: s.player_name ?? '', character_name: s.character_name ?? '' };
    }
    edits = map;
    editing = true;
    collapsed = false;
    error = null;
  }

  function cancelBatchEdit() {
    editing = false;
    edits = {};
    error = null;
  }

  function selectFromRoster(speakerId: number, entry: RosterEntry) {
    edits[speakerId] = { player_name: entry.player_name, character_name: entry.character_name };
  }

  async function saveAll() {
    saving = true;
    error = null;
    try {
      const promises = speakers.map(s =>
        api.put(`/speakers/${s.id}`, {
          player_name: edits[s.id]?.player_name ?? '',
          character_name: edits[s.id]?.character_name ?? '',
        })
      );
      await Promise.all(promises);
      editing = false;
      edits = {};
      await load();
      onUpdate();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to save speakers';
      // Reload to show any partial updates
      await load();
    } finally {
      saving = false;
    }
  }

  async function generateSignatures() {
    generating = true;
    error = null;
    generateResult = null;
    try {
      const result = await api.post<{ signatures_generated: number; speakers: Array<{ player_name: string; character_name: string; num_samples: number }> }>(
        `/sessions/${sessionId}/generate-voice-signatures`
      );
      if (result.signatures_generated === 0) {
        generateResult = 'No signatures generated. Make sure speakers are assigned to roster entries.';
      } else {
        const details = result.speakers.map(s => `${s.character_name} (${s.player_name}): ${s.num_samples} samples`).join(', ');
        generateResult = `Generated ${result.signatures_generated} voice signature(s): ${details}`;
      }
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to generate voice signatures';
    } finally {
      generating = false;
    }
  }

  function speakerDisplay(s: Speaker): string {
    if (s.character_name && s.player_name) return `${s.character_name} (${s.player_name})`;
    if (s.character_name) return s.character_name;
    if (s.player_name) return s.player_name;
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
  <div class="panel-header" role="button" tabindex="0" onclick={() => { if (!editing) collapsed = !collapsed; }} onkeydown={(e: KeyboardEvent) => { if (!editing && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); collapsed = !collapsed; } }}>
    <h4>
      <span class="collapse-icon" class:collapsed>&#9656;</span>
      Speakers
      {#if speakers.length > 0}
        <span class="speaker-count">{speakers.length}</span>
      {/if}
    </h4>
    <div class="header-actions">
      {#if !collapsed}
        {#if hasAudio && hasRosterLinkedSpeaker && !editing}
          <button class="btn btn-sm btn-voice" onclick={(e: MouseEvent) => { e.stopPropagation(); generateSignatures(); }} disabled={generating}>
            {generating ? 'Generating...' : 'Generate Voice Signatures'}
          </button>
        {/if}
        {#if speakers.length > 0 && !editing}
          <button class="btn btn-sm" onclick={(e: MouseEvent) => { e.stopPropagation(); startBatchEdit(); }}>Edit All</button>
        {/if}
      {/if}
    </div>
  </div>

  {#if !collapsed}
    {#if error}
      <div class="error">{error}</div>
    {/if}

    {#if generateResult}
      <div class="success">{generateResult}</div>
    {/if}

    {#if editing}
      <div class="batch-form">
        {#each speakers as s}
          <div class="batch-row">
            <span class="speaker-badge" style="background: {speakerColor(s.diarization_label)}">
              {s.diarization_label}
            </span>
            <div class="batch-inputs">
              <input type="text" placeholder="Player name" bind:value={edits[s.id].player_name} />
              <input type="text" placeholder="Character name" bind:value={edits[s.id].character_name} />
              {#if roster.length > 0}
                <div class="roster-suggestions">
                  {#each roster as r}
                    <button class="roster-btn" onclick={() => selectFromRoster(s.id, r)}>
                      {r.character_name} ({r.player_name})
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        {/each}
        <div class="btn-group">
          <button class="btn btn-primary" onclick={saveAll} disabled={saving}>
            {saving ? 'Saving...' : 'Save All'}
          </button>
          <button class="btn" onclick={cancelBatchEdit} disabled={saving}>Cancel</button>
        </div>
      </div>
    {:else}
      {#each speakers as s}
        <div class="speaker-row">
          <span class="speaker-badge" style="background: {speakerColor(s.diarization_label)}">
            {speakerDisplay(s)}
          </span>
          {#if hasSignature(s)}
            <span class="signature-badge" title="Voice signature enrolled">VS</span>
          {/if}
        </div>
      {/each}
    {/if}

    {#if speakers.length === 0}
      <p class="empty">No speakers detected yet.</p>
    {/if}
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

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    background: none;
    border: none;
    padding: 0;
    color: inherit;
    font: inherit;
    cursor: pointer;
    text-align: left;
  }

  .panel-header:not(:last-child) {
    margin-bottom: 0.75rem;
  }

  .panel-header h4 {
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .collapse-icon {
    display: inline-block;
    transition: transform 0.2s ease;
    transform: rotate(90deg);
    font-size: 0.85rem;
  }

  .collapse-icon.collapsed {
    transform: rotate(0deg);
  }

  .speaker-count {
    font-size: 0.75rem;
    font-weight: 400;
    color: var(--text-faint);
  }

  .header-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .error {
    background: var(--error-bg);
    border: 1px solid var(--accent);
    color: var(--accent);
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    font-size: 0.85rem;
    margin-bottom: 0.75rem;
  }

  .success {
    background: color-mix(in srgb, var(--btn-green) 15%, transparent);
    border: 1px solid var(--btn-green);
    color: var(--btn-green);
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    font-size: 0.85rem;
    margin-bottom: 0.75rem;
  }

  .speaker-row {
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .speaker-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    color: #fff;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .signature-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    background: var(--btn-green);
    color: #fff;
    font-size: 0.6rem;
    font-weight: 700;
    flex-shrink: 0;
  }

  .batch-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .batch-row {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
  }

  .batch-row .speaker-badge {
    flex-shrink: 0;
    margin-top: 0.3rem;
  }

  .batch-inputs {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
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
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-sm { padding: 0.25rem 0.5rem; }
  .btn-voice { background: var(--btn-green); border-color: var(--btn-green); color: #fff; }
  .btn-voice:hover { opacity: 0.9; background: var(--btn-green); }
  .btn-group { display: flex; gap: 0.5rem; }

  .empty { color: var(--text-faint); font-size: 0.85rem; }
</style>
