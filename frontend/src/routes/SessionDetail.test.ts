import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import SessionDetail from './SessionDetail.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    del: vi.fn().mockResolvedValue({}),
  },
  reDiarize: vi.fn(),
  generateImageStream: vi.fn(),
  mergeSpeakers: vi.fn(),
  uploadAudio: vi.fn(),
  processAudio: vi.fn(),
}));

import { api } from '../lib/api';

const mockSession = {
  id: 1,
  campaign_id: 10,
  name: 'Dragon Siege',
  date: '2025-01-15',
  status: 'completed',
  audio_path: '/audio/session1.wav',
  language: 'en',
  session_number: 1,
};

function setupMocks(session = mockSession) {
  vi.mocked(api.get).mockImplementation((path: string) => {
    if (path.match(/^\/sessions\/\d+$/)) return Promise.resolve(session);
    if (path.includes('/transcript')) return Promise.resolve([]);
    if (path.includes('/speakers')) return Promise.resolve([]);
    if (path.includes('/roster')) return Promise.resolve([]);
    if (path.includes('/voice-signatures')) return Promise.resolve([]);
    if (path.includes('/summaries')) return Promise.resolve([]);
    if (path.includes('/images')) return Promise.resolve([]);
    if (path.includes('/llm/status')) return Promise.resolve({ status: 'ok' });
    if (path.includes('/image-health')) return Promise.resolve({ status: 'ok' });
    if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
    return Promise.resolve({});
  });
}

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('SessionDetail', () => {
  afterEach(() => {
    cleanup();
    vi.mocked(api.get).mockReset();
  });

  it('shows loading state initially', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    render(SessionDetail, { props: { sessionId: 1 } });
    expect(screen.getByText(/Loading session/)).toBeInTheDocument();
  });

  it('shows session name after loading', async () => {
    setupMocks();
    render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Dragon Siege')).toBeInTheDocument();
  });

  it('shows session metadata', async () => {
    setupMocks();
    render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText(/2025-01-15/)).toBeInTheDocument();
    expect(screen.getByText(/completed/)).toBeInTheDocument();
    expect(screen.getByText(/EN/)).toBeInTheDocument();
  });

  it('renders all tab buttons', async () => {
    setupMocks();
    render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Recording')).toBeInTheDocument();
    expect(screen.getByText('Chronicle')).toBeInTheDocument();
    expect(screen.getByText('Tales')).toBeInTheDocument();
    expect(screen.getByText('Visions')).toBeInTheDocument();
    expect(screen.getByText('Export')).toBeInTheDocument();
  });

  it('defaults to recording tab', async () => {
    setupMocks();
    const { container } = render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    const tabs = container.querySelectorAll('.tab');
    expect(tabs[0]?.classList.contains('active')).toBe(true);
  });

  it('switches tabs on click', async () => {
    setupMocks();
    const { container } = render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Chronicle'));
    const tabs = container.querySelectorAll('.tab');
    expect(tabs[1]?.classList.contains('active')).toBe(true);
  });

  it('shows regenerate name button for completed sessions', async () => {
    setupMocks();
    render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Regenerate Name')).toBeInTheDocument();
  });

  it('does not show regenerate name for draft sessions', async () => {
    setupMocks({ ...mockSession, status: 'draft' });
    render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    expect(screen.queryByText('Regenerate Name')).not.toBeInTheDocument();
  });

  it('allows editing session name', async () => {
    setupMocks();
    render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Dragon Siege'));
    const input = screen.getByDisplayValue('Dragon Siege');
    expect(input).toBeInTheDocument();
  });

  it('shows audio player when session has audio', async () => {
    setupMocks();
    const { container } = render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    // Switch to transcript tab to see audio player
    await fireEvent.click(screen.getByText('Chronicle'));
    await flush();
    const audioPlayer = container.querySelector('.audio-player');
    expect(audioPlayer).toBeInTheDocument();
  });

  it('does not show audio player when session has no audio', async () => {
    setupMocks({ ...mockSession, audio_path: null });
    const { container } = render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Chronicle'));
    await flush();
    const audioPlayer = container.querySelector('.audio-player');
    expect(audioPlayer).not.toBeInTheDocument();
  });

  it('shows tab hints with numbers', async () => {
    setupMocks();
    const { container } = render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    const hints = container.querySelectorAll('.tab-hint');
    expect(hints.length).toBe(5);
    expect(hints[0].textContent).toBe('1');
    expect(hints[1].textContent).toBe('2');
  });

  it('shows speaker panel in transcript tab', async () => {
    setupMocks();
    const { container } = render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Chronicle'));
    await flush();
    const speakerPanel = container.querySelector('.speaker-panel');
    expect(speakerPanel).toBeInTheDocument();
  });

  it('shows summary section in tales tab', async () => {
    setupMocks();
    render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Tales'));
    await flush();
    expect(screen.getByText('Generate Summary')).toBeInTheDocument();
  });

  it('shows illustrations section in visions tab', async () => {
    setupMocks();
    render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Visions'));
    await flush();
    expect(screen.getByText('Generate Scene')).toBeInTheDocument();
  });

  it('shows export section in export tab', async () => {
    setupMocks();
    render(SessionDetail, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Export'));
    await flush();
    const elements = screen.getAllByText('Export Transcript');
    expect(elements.length).toBe(2); // heading + button
  });
});
