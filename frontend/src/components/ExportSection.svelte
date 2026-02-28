<script lang="ts">
  import { api } from '../lib/api';

  type Props = { sessionId: number };
  let { sessionId }: Props = $props();

  type Summary = { id: number; type: string; content: string; character_name?: string; player_name?: string };

  let summaries = $state<Summary[]>([]);
  let toast = $state<string | null>(null);
  let emailSummaryId = $state<number | null>(null);
  let emailTo = $state('');
  let emailSubject = $state('');
  let emailBody = $state('');
  let sending = $state(false);

  async function load() {
    summaries = await api.get<Summary[]>(`/sessions/${sessionId}/summaries`);
  }

  function showToast(msg: string) {
    toast = msg;
    setTimeout(() => { toast = null; }, 3000);
  }

  async function copyToClipboard(text: string) {
    await navigator.clipboard.writeText(text);
    showToast('Copied to clipboard');
  }

  function downloadFile(url: string) {
    const a = document.createElement('a');
    a.href = url;
    a.download = '';
    a.click();
  }

  async function prepareEmail(summaryId: number) {
    const content = await api.get<{ subject: string; body: string }>(`/summaries/${summaryId}/email-content`);
    emailSummaryId = summaryId;
    emailSubject = content.subject;
    emailBody = content.body;
  }

  async function sendEmail() {
    if (!emailSummaryId || !emailTo.trim()) return;
    sending = true;
    try {
      await api.post(`/summaries/${emailSummaryId}/send-email`, { to: emailTo });
      showToast('Email sent successfully');
      emailSummaryId = null;
      emailTo = '';
    } catch (e: any) {
      showToast(`Failed: ${e.message}`);
    } finally {
      sending = false;
    }
  }

  $effect(() => { load(); });

  let fullSummaries = $derived(summaries.filter(s => s.type === 'full'));
  let povSummaries = $derived(summaries.filter(s => s.type === 'pov'));
</script>

<div class="export-section">
  {#if toast}
    <div class="toast">{toast}</div>
  {/if}

  <h3>Export Transcript</h3>
  <button class="btn" onclick={() => downloadFile(`/api/sessions/${sessionId}/export/transcript`)}>
    Export Transcript
  </button>

  {#if fullSummaries.length > 0}
    <h3>Session Summary</h3>
    {#each fullSummaries as s}
      <div class="export-row">
        <button class="btn" onclick={() => downloadFile(`/api/summaries/${s.id}/export/pdf`)}>Export PDF</button>
        <button class="btn" onclick={() => downloadFile(`/api/summaries/${s.id}/export/text`)}>Export Text</button>
        <button class="btn" onclick={() => copyToClipboard(s.content)}>Copy to Clipboard</button>
        <button class="btn" onclick={() => prepareEmail(s.id)}>Prepare Email</button>
      </div>
    {/each}
  {/if}

  {#if povSummaries.length > 0}
    <h3>Character POV Summaries</h3>
    <button class="btn" onclick={() => downloadFile(`/api/sessions/${sessionId}/export/pov-all`)}>
      Export All POV Summaries (ZIP)
    </button>
    {#each povSummaries as s}
      <div class="export-row">
        <span class="label">{s.character_name ?? 'Unknown'}</span>
        <button class="btn btn-sm" onclick={() => downloadFile(`/api/summaries/${s.id}/export/pdf`)}>PDF</button>
        <button class="btn btn-sm" onclick={() => downloadFile(`/api/summaries/${s.id}/export/text`)}>Text</button>
        <button class="btn btn-sm" onclick={() => copyToClipboard(s.content)}>Copy</button>
        <button class="btn btn-sm" onclick={() => prepareEmail(s.id)}>Email</button>
      </div>
    {/each}
  {/if}

  {#if emailSummaryId !== null}
    <div class="email-dialog">
      <h4>Prepare Email</h4>
      <div class="email-field">
        <label>Subject</label>
        <div class="email-row">
          <input type="text" bind:value={emailSubject} readonly />
          <button class="btn btn-sm" onclick={() => copyToClipboard(emailSubject)}>Copy</button>
        </div>
      </div>
      <div class="email-field">
        <label>Body</label>
        <div class="email-row">
          <textarea readonly>{emailBody}</textarea>
          <button class="btn btn-sm" onclick={() => copyToClipboard(emailBody)}>Copy</button>
        </div>
      </div>
      <div class="email-field">
        <label>Send directly (requires SMTP config)</label>
        <div class="email-row">
          <input type="email" placeholder="recipient@example.com" bind:value={emailTo} />
          <button class="btn btn-primary btn-sm" onclick={sendEmail} disabled={sending}>
            {sending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
      <button class="btn btn-sm" onclick={() => (emailSummaryId = null)}>Close</button>
    </div>
  {/if}

  {#if summaries.length === 0}
    <p class="empty">No summaries to export. Generate summaries first.</p>
  {/if}
</div>

<style>
  .export-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .export-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .label {
    font-weight: 600;
    color: var(--accent);
    min-width: 120px;
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
    animation: fadeIn 0.2s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .email-dialog {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
  }

  .email-dialog h4 { margin: 0 0 1rem; }

  .email-field {
    margin-bottom: 0.75rem;
  }

  .email-field label {
    display: block;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
  }

  .email-row {
    display: flex;
    gap: 0.5rem;
  }

  input, textarea {
    flex: 1;
    padding: 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
  }

  textarea {
    min-height: 100px;
    resize: vertical;
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
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-sm { padding: 0.25rem 0.75rem; font-size: 0.8rem; }

  .empty { color: var(--text-faint); text-align: center; padding: 2rem; }
</style>
