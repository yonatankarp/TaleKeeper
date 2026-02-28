<script lang="ts">
  import { WHISPER_LANGUAGES } from '../lib/languages';

  type Props = {
    value: string;
    onchange: (code: string) => void;
    compact?: boolean;
  };
  let { value, onchange, compact = false }: Props = $props();

  let search = $state('');
  let open = $state(false);
  let inputEl: HTMLInputElement | undefined = $state();
  let highlightedIndex = $state(-1);
  let dropdownEl: HTMLUListElement | undefined = $state();

  let filtered = $derived(
    search
      ? WHISPER_LANGUAGES.filter(
          (l) =>
            l.name.toLowerCase().includes(search.toLowerCase()) ||
            l.code.toLowerCase().includes(search.toLowerCase())
        )
      : WHISPER_LANGUAGES
  );

  let selectedName = $derived(
    WHISPER_LANGUAGES.find((l) => l.code === value)?.name ?? value
  );

  // Reset highlighted index when filter changes
  $effect(() => {
    filtered;
    highlightedIndex = -1;
  });

  function select(code: string) {
    onchange(code);
    search = '';
    open = false;
    highlightedIndex = -1;
  }

  function handleFocus() {
    open = true;
    search = '';
    highlightedIndex = -1;
  }

  function handleBlur() {
    // Delay to allow click on option
    setTimeout(() => { open = false; search = ''; highlightedIndex = -1; }, 150);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!open) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      highlightedIndex = Math.min(highlightedIndex + 1, filtered.length - 1);
      scrollToHighlighted();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      highlightedIndex = Math.max(highlightedIndex - 1, 0);
      scrollToHighlighted();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0 && highlightedIndex < filtered.length) {
        select(filtered[highlightedIndex].code);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      open = false;
      search = '';
      highlightedIndex = -1;
    }
  }

  function scrollToHighlighted() {
    requestAnimationFrame(() => {
      if (!dropdownEl) return;
      const item = dropdownEl.children[highlightedIndex] as HTMLElement | undefined;
      item?.scrollIntoView({ block: 'nearest' });
    });
  }
</script>

<div class="lang-select" class:compact>
  <input
    bind:this={inputEl}
    type="text"
    placeholder={selectedName}
    bind:value={search}
    onfocus={handleFocus}
    onblur={handleBlur}
    onkeydown={handleKeydown}
  />
  {#if open}
    <ul class="dropdown" bind:this={dropdownEl}>
      {#each filtered as lang, i}
        <li>
          <button
            class="option"
            class:selected={lang.code === value}
            class:highlighted={i === highlightedIndex}
            onmousedown={() => select(lang.code)}
          >
            {lang.name} <span class="code">({lang.code})</span>
          </button>
        </li>
      {/each}
      {#if filtered.length === 0}
        <li class="no-results">No languages found</li>
      {/if}
    </ul>
  {/if}
</div>

<style>
  .lang-select {
    position: relative;
    width: 100%;
  }

  .lang-select.compact {
    width: auto;
    display: inline-block;
    min-width: 160px;
  }

  input {
    width: 100%;
    padding: 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.85rem;
    box-sizing: border-box;
  }

  .compact input {
    padding: 0.3rem 0.5rem;
    font-size: 0.8rem;
  }

  .dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    max-height: 200px;
    overflow-y: auto;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    margin: 2px 0 0;
    padding: 0;
    list-style: none;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .option {
    display: block;
    width: 100%;
    padding: 0.4rem 0.75rem;
    background: none;
    border: none;
    color: var(--text);
    font: inherit;
    font-size: 0.85rem;
    text-align: left;
    cursor: pointer;
  }

  .option:hover,
  .option.highlighted {
    background: var(--bg-hover);
  }

  .option.selected {
    color: var(--accent);
    font-weight: 600;
  }

  .code {
    color: var(--text-faint);
    font-size: 0.75rem;
  }

  .no-results {
    padding: 0.5rem 0.75rem;
    color: var(--text-muted);
    font-size: 0.85rem;
  }
</style>
