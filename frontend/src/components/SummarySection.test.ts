import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import SummarySection from './SummarySection.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
}));

import { api } from '../lib/api';

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('SummarySection', () => {
  afterEach(() => {
    cleanup();
    vi.mocked(api.get).mockReset();
  });

  function setupMocks(summaries: unknown[] = []) {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/summaries')) return Promise.resolve(summaries);
      if (path.includes('/llm/status')) return Promise.resolve({ status: 'ok' });
      return Promise.resolve({});
    });
  }

  it('renders "Generate Summary" button', async () => {
    setupMocks();
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Generate Summary')).toBeInTheDocument();
  });

  it('renders "Generate POV Summaries" button', async () => {
    setupMocks();
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Generate POV Summaries')).toBeInTheDocument();
  });

  it('shows "No summaries generated yet" when empty', async () => {
    setupMocks();
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText(/No summaries generated yet/)).toBeInTheDocument();
  });

  it('shows LLM warning when LLM status is not ok', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/summaries')) return Promise.resolve([]);
      if (path.includes('/llm/status')) return Promise.resolve({ status: 'error', message: 'Cannot connect' });
      return Promise.resolve({});
    });
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('LLM provider not available')).toBeInTheDocument();
  });

  it('shows summary content when summaries exist', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'The heroes fought the dragon.', model_used: 'llama3', generated_at: '2025-01-01' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('The heroes fought the dragon.')).toBeInTheDocument();
    expect(screen.getByText('Session Summary')).toBeInTheDocument();
  });

  it('shows summary hint about generation time', async () => {
    setupMocks();
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText(/Summary generation may take/)).toBeInTheDocument();
  });

  it('shows edit and delete buttons for full summaries', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Summary text', model_used: 'llama3', generated_at: '2025-01-01' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByText('Regenerate')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('shows model and generation info', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Text', model_used: 'llama3.1:8b', generated_at: '2025-03-01' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Model: llama3.1:8b')).toBeInTheDocument();
    expect(screen.getByText('Generated: 2025-03-01')).toBeInTheDocument();
  });

  it('shows POV summary with character heading', async () => {
    setupMocks([
      { id: 2, type: 'pov', content: 'POV text', model_used: 'llama3', generated_at: '2025-01-01', character_name: 'Gandalf', player_name: 'Alice' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Character POV Summaries')).toBeInTheDocument();
    expect(screen.getByText('Gandalf (Alice)')).toBeInTheDocument();
  });

  it('shows Clear All button when summaries exist', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Text', model_used: 'llama3', generated_at: '2025-01-01' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Clear All')).toBeInTheDocument();
  });

  it('shows confirm dialog when Delete is clicked', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Text', model_used: 'llama3', generated_at: '2025-01-01' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Delete'));
    expect(screen.getByText('Delete Summary')).toBeInTheDocument();
  });

  it('disables generate buttons when LLM is unavailable', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/summaries')) return Promise.resolve([]);
      if (path.includes('/llm/status')) return Promise.resolve({ status: 'error' });
      return Promise.resolve({});
    });
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    const generateBtn = screen.getByText('Generate Summary');
    expect(generateBtn).toBeDisabled();
  });

  it('calls api.post when Generate Summary is clicked', async () => {
    setupMocks();
    vi.mocked(api.post).mockResolvedValue({});
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Generate Summary'));
    await flush();
    expect(api.post).toHaveBeenCalledWith('/sessions/1/generate-summary', { type: 'full' });
  });

  it('calls api.post when Generate POV Summaries is clicked', async () => {
    setupMocks();
    vi.mocked(api.post).mockResolvedValue({});
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Generate POV Summaries'));
    await flush();
    expect(api.post).toHaveBeenCalledWith('/sessions/1/generate-summary', { type: 'pov' });
  });

  it('enters edit mode when Edit button is clicked', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Summary text', model_used: 'llama3', generated_at: '2025-01-01' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Edit'));
    await flush();
    expect(screen.getByText('Save')).toBeInTheDocument();
  });

  it('saves edited summary', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Summary text', model_used: 'llama3', generated_at: '2025-01-01' },
    ]);
    vi.mocked(api.put).mockResolvedValue({});
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Edit'));
    await flush();
    await fireEvent.click(screen.getByText('Save'));
    await flush();
    expect(api.put).toHaveBeenCalledWith('/summaries/1', { content: 'Summary text' });
  });

  it('calls api.del when delete is confirmed', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Text', model_used: 'llama3', generated_at: '2025-01-01' },
    ]);
    vi.mocked(api.del).mockResolvedValue({});
    const { container } = render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Delete'));
    // The confirm dialog has a btn-danger button
    const confirmBtn = container.querySelector('.dialog .btn-danger') as HTMLButtonElement;
    await fireEvent.click(confirmBtn);
    await flush();
    expect(api.del).toHaveBeenCalledWith('/summaries/1');
  });

  it('shows Regenerate All POV button when POV summaries exist', async () => {
    setupMocks([
      { id: 2, type: 'pov', content: 'POV text', model_used: 'llama3', generated_at: '2025-01-01', character_name: 'Gandalf', player_name: 'Alice' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Regenerate All POV')).toBeInTheDocument();
  });

  it('shows confirm dialog when Regenerate is clicked', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Text', model_used: 'llama3', generated_at: '2025-01-01' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Regenerate'));
    expect(screen.getByText('Regenerate Summaries')).toBeInTheDocument();
  });

  it('shows confirm dialog when Clear All is clicked', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Text', model_used: 'llama3', generated_at: '2025-01-01' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Clear All'));
    expect(screen.getByText('Clear All Summaries')).toBeInTheDocument();
  });

  it('shows LLM warning message text', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/summaries')) return Promise.resolve([]);
      if (path.includes('/llm/status')) return Promise.resolve({ status: 'error', message: 'Model not loaded' });
      return Promise.resolve({});
    });
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText(/Model not loaded/)).toBeInTheDocument();
  });

  it('shows both full and POV summaries together', async () => {
    setupMocks([
      { id: 1, type: 'full', content: 'Full summary', model_used: 'llama3', generated_at: '2025-01-01' },
      { id: 2, type: 'pov', content: 'POV text', model_used: 'llama3', generated_at: '2025-01-01', character_name: 'Gandalf', player_name: 'Alice' },
    ]);
    render(SummarySection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Session Summary')).toBeInTheDocument();
    expect(screen.getByText('Character POV Summaries')).toBeInTheDocument();
  });
});
