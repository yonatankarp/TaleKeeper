## 1. Replace conditional rendering with CSS visibility

- [x] 1.1 Replace the `{#if}`/`{:else if}` tab-content block in SessionDetail.svelte with four always-rendered `<div>` wrappers (one per tab: recording, transcript, summaries, export)
- [x] 1.2 Add `class:hidden={activeTab !== '<tab>'}` directive to each wrapper div
- [x] 1.3 Keep `{#if hasAudio}` guard on AudioPlayer inside the transcript wrapper (data dependency, not tab visibility)

## 2. CSS

- [x] 2.1 Add `.hidden { display: none; }` rule to the SessionDetail component styles

## 3. Verification

- [x] 3.1 Verify recording continues uninterrupted when switching to transcript tab and back
- [x] 3.2 Verify tab state is preserved across switches (no re-mount, no data re-fetch)
