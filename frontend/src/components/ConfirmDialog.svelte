<script lang="ts">
  type Props = {
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    onconfirm: () => void;
    oncancel: () => void;
  };
  let { title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', onconfirm, oncancel }: Props = $props();

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') oncancel();
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) oncancel();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="backdrop" onclick={handleBackdropClick}>
  <div class="dialog">
    <h3>{title}</h3>
    <p>{message}</p>
    <div class="btn-group">
      <button class="btn" onclick={oncancel}>{cancelLabel}</button>
      <button class="btn btn-danger" onclick={onconfirm}>{confirmLabel}</button>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 300;
    animation: fadeIn 0.15s ease;
  }

  .dialog {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    max-width: 420px;
    width: 90%;
    animation: scaleIn 0.15s ease;
  }

  .dialog h3 {
    margin: 0 0 0.75rem;
  }

  .dialog p {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin: 0 0 1.25rem;
    line-height: 1.5;
  }

  .btn-group {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
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

  .btn-danger {
    background: var(--danger);
    border-color: var(--danger);
    color: #fff;
  }

  .btn-danger:hover {
    background: var(--danger);
    opacity: 0.85;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
  }
</style>
