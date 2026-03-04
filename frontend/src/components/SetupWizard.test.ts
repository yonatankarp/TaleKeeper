import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn().mockResolvedValue({}),
    del: vi.fn(),
  },
}));

import { api } from '../lib/api';
import SetupWizard from './SetupWizard.svelte';

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('SetupWizard', () => {
  afterEach(() => cleanup());

  function mockSetupStatus(overrides = {}) {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path === '/setup-status')
        return Promise.resolve({
          is_first_run: true,
          data_dir_exists: true,
          llm_connected: false,
          image_connected: false,
          data_dir: '/data',
          ...overrides,
        });
      if (path === '/settings') return Promise.resolve({});
      return Promise.resolve({});
    });
  }

  function makeProps(overrides = {}) {
    return {
      onDismiss: vi.fn(),
      ...overrides,
    };
  }

  it('renders "Welcome to TaleKeeper" title', () => {
    mockSetupStatus();
    render(SetupWizard, { props: makeProps() });
    expect(screen.getByText('Welcome to TaleKeeper')).toBeInTheDocument();
  });

  it('shows setup checks after loading', async () => {
    mockSetupStatus();
    render(SetupWizard, { props: makeProps() });
    await flush();
    expect(screen.getByText('Data directory')).toBeInTheDocument();
    expect(screen.getByText(/LLM Provider/)).toBeInTheDocument();
    expect(screen.getByText(/Image Generation/)).toBeInTheDocument();
  });

  it('shows "Continue Anyway" when LLM is not connected', async () => {
    mockSetupStatus({ llm_connected: false });
    render(SetupWizard, { props: makeProps() });
    await flush();
    expect(screen.getByText('Continue Anyway')).toBeInTheDocument();
  });

  it('shows "Get Started" when LLM is connected', async () => {
    mockSetupStatus({ llm_connected: true });
    render(SetupWizard, { props: makeProps() });
    await flush();
    expect(screen.getByText('Get Started')).toBeInTheDocument();
  });

  it('calls onDismiss when dismiss button is clicked', async () => {
    mockSetupStatus({ llm_connected: true });
    const onDismiss = vi.fn();
    render(SetupWizard, { props: makeProps({ onDismiss }) });
    await flush();
    await fireEvent.click(screen.getByText('Get Started'));
    await flush();
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it('shows "Re-check" button', async () => {
    mockSetupStatus();
    render(SetupWizard, { props: makeProps() });
    await flush();
    expect(screen.getByText('Re-check')).toBeInTheDocument();
  });

  it('shows HuggingFace token section', async () => {
    mockSetupStatus();
    render(SetupWizard, { props: makeProps() });
    await flush();
    expect(screen.getByText(/HuggingFace Token/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText('hf_...')).toBeInTheDocument();
  });

  it('includes hf_token when saving settings', async () => {
    mockSetupStatus();
    render(SetupWizard, { props: makeProps() });
    await flush();

    const input = screen.getByPlaceholderText('hf_...');
    await fireEvent.input(input, { target: { value: 'hf_test123' } });
    await fireEvent.click(screen.getByText('Re-check'));
    await flush();

    expect(api.put).toHaveBeenCalledWith('/settings', {
      settings: expect.objectContaining({ hf_token: 'hf_test123' }),
    });
  });
});
