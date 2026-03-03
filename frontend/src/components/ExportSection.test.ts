import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import ExportSection from './ExportSection.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue([]),
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

describe('ExportSection', () => {
  afterEach(() => {
    cleanup();
    vi.mocked(api.get).mockReset().mockResolvedValue([]);
  });

  it('shows "Export Transcript" heading and button', async () => {
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    const elements = screen.getAllByText('Export Transcript');
    expect(elements.length).toBe(2); // h3 heading + button
    expect(elements[1].tagName).toBe('BUTTON');
  });

  it('shows "No summaries to export" when no summaries', async () => {
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText(/No summaries to export/)).toBeInTheDocument();
  });

  it('shows full summary export options when full summaries exist', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, type: 'full', content: 'A great adventure', character_name: null, player_name: null },
    ]);
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Session Summary')).toBeInTheDocument();
    expect(screen.getByText('Export PDF')).toBeInTheDocument();
    expect(screen.getByText('Export Text')).toBeInTheDocument();
    expect(screen.getByText('Copy to Clipboard')).toBeInTheDocument();
    expect(screen.getByText('Share via Email')).toBeInTheDocument();
  });

  it('shows POV summary export options with character name', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 2, type: 'pov', content: 'Gandalf saw the dragon', character_name: 'Gandalf', player_name: 'Alice' },
    ]);
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Character POV Summaries')).toBeInTheDocument();
    expect(screen.getByText('Gandalf')).toBeInTheDocument();
  });

  it('shows batch export buttons when summaries exist', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, type: 'full', content: 'Summary', character_name: null, player_name: null },
    ]);
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Batch Export')).toBeInTheDocument();
    expect(screen.getByText('Export All PDFs (ZIP)')).toBeInTheDocument();
    expect(screen.getByText('Export All Printable (ZIP)')).toBeInTheDocument();
  });

  it('opens email dialog when Share via Email is clicked', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/summaries') && !path.includes('/email')) {
        return Promise.resolve([
          { id: 1, type: 'full', content: 'Summary', character_name: null, player_name: null },
        ]);
      }
      if (path.includes('/email-content')) {
        return Promise.resolve({ subject: 'Session Recap', body: 'Full summary text' });
      }
      return Promise.resolve({});
    });
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Share via Email'));
    await flush();
    expect(screen.getByText('Share via Email', { selector: 'h4' })).toBeInTheDocument();
  });

  it('shows print PDF buttons for full summaries', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, type: 'full', content: 'Summary', character_name: null, player_name: null },
    ]);
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Print PDF')).toBeInTheDocument();
  });

  it('shows POV summary buttons (PDF, Print, Text, Copy, Email)', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 2, type: 'pov', content: 'POV text', character_name: 'Gandalf', player_name: 'Alice' },
    ]);
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('PDF')).toBeInTheDocument();
    expect(screen.getByText('Print')).toBeInTheDocument();
    expect(screen.getByText('Text')).toBeInTheDocument();
    expect(screen.getByText('Copy')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
  });

  it('shows email dialog fields when email is opened', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/summaries') && !path.includes('/email')) {
        return Promise.resolve([
          { id: 1, type: 'full', content: 'Summary', character_name: null, player_name: null },
        ]);
      }
      if (path.includes('/email-content')) {
        return Promise.resolve({ subject: 'Session Recap', body: 'Full summary text' });
      }
      return Promise.resolve({});
    });
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Share via Email'));
    await flush();
    expect(screen.getByText('Subject')).toBeInTheDocument();
    expect(screen.getByText('Body')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('recipient@example.com')).toBeInTheDocument();
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  it('shows Close button in email dialog', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/summaries') && !path.includes('/email')) {
        return Promise.resolve([
          { id: 1, type: 'full', content: 'Summary', character_name: null, player_name: null },
        ]);
      }
      if (path.includes('/email-content')) {
        return Promise.resolve({ subject: 'Recap', body: 'Body text' });
      }
      return Promise.resolve({});
    });
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Share via Email'));
    await flush();
    expect(screen.getByText('Close')).toBeInTheDocument();
  });

  it('shows Unknown for POV character without character_name', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 2, type: 'pov', content: 'POV text', character_name: null, player_name: null },
    ]);
    render(ExportSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });
});
