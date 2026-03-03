import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('wizard', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('starts closed', async () => {
    const { wizard } = await import('./wizard.svelte');
    expect(wizard.open).toBe(false);
  });

  it('show() opens the wizard', async () => {
    const { wizard } = await import('./wizard.svelte');
    wizard.show();
    expect(wizard.open).toBe(true);
  });

  it('hide() closes the wizard', async () => {
    const { wizard } = await import('./wizard.svelte');
    wizard.show();
    expect(wizard.open).toBe(true);
    wizard.hide();
    expect(wizard.open).toBe(false);
  });

  it('can toggle multiple times', async () => {
    const { wizard } = await import('./wizard.svelte');
    wizard.show();
    wizard.hide();
    wizard.show();
    expect(wizard.open).toBe(true);
  });
});
