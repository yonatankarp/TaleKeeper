import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import SpeakerPanel from './SpeakerPanel.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
  mergeSpeakers: vi.fn(),
}));

import { api } from '../lib/api';

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('SpeakerPanel', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue([]);
  });

  function makeProps(overrides = {}) {
    return {
      sessionId: 1,
      campaignId: 10,
      hasAudio: false,
      onUpdate: vi.fn(),
      ...overrides,
    };
  }

  it('renders "Speakers" heading', () => {
    render(SpeakerPanel, { props: makeProps() });
    expect(screen.getByText('Speakers')).toBeInTheDocument();
  });

  it('starts in collapsed state', () => {
    render(SpeakerPanel, { props: makeProps() });
    expect(screen.queryByText('No speakers detected yet.')).not.toBeInTheDocument();
  });

  it('shows "No speakers detected yet." when expanded with no speakers', async () => {
    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    expect(screen.getByText('No speakers detected yet.')).toBeInTheDocument();
  });

  it('clicking header expands the panel', async () => {
    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    expect(screen.getByText('No speakers detected yet.')).toBeInTheDocument();
  });

  it('shows speaker badges when speakers are loaded', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPEAKER_00', player_name: 'Alice', character_name: 'Gandalf' },
      { id: 2, diarization_label: 'SPEAKER_01', player_name: 'Bob', character_name: 'Frodo' },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    expect(screen.getByText('Gandalf (Alice)')).toBeInTheDocument();
    expect(screen.getByText('Frodo (Bob)')).toBeInTheDocument();
  });

  it('shows speaker count when speakers exist', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPEAKER_00', player_name: 'Alice', character_name: 'Gandalf' },
      { id: 2, diarization_label: 'SPEAKER_01', player_name: 'Bob', character_name: 'Frodo' },
      { id: 3, diarization_label: 'SPEAKER_02', player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('shows Edit All button when speakers exist and expanded', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPEAKER_00', player_name: 'Alice', character_name: 'Gandalf' },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    expect(screen.getByText('Edit All')).toBeInTheDocument();
  });

  it('shows diarization label when no player or character name', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPEAKER_00', player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    expect(screen.getByText('SPEAKER_00')).toBeInTheDocument();
  });

  it('shows character name only for speaker with no player name', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPK', player_name: null, character_name: 'Gandalf' },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    expect(screen.getByText('Gandalf')).toBeInTheDocument();
  });

  it('shows player name only for speaker with no character name', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPK', player_name: 'Alice', character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });

  it('shows batch edit form when Edit All is clicked', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPEAKER_00', player_name: 'Alice', character_name: 'Gandalf' },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      if (path.includes('/transcript')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    await fireEvent.click(screen.getByText('Edit All'));
    await flush();
    expect(screen.getByText('Save All')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('shows roster suggestions in batch edit when roster entries exist', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPEAKER_00', player_name: null, character_name: null },
    ];
    const roster = [
      { id: 10, player_name: 'Alice', character_name: 'Gandalf', is_active: 1 },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve(roster);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      if (path.includes('/transcript')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    await fireEvent.click(screen.getByText('Edit All'));
    await flush();
    expect(screen.getByText('Gandalf (Alice)')).toBeInTheDocument();
  });

  it('cancels batch edit', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPEAKER_00', player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      if (path.includes('/transcript')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    await fireEvent.click(screen.getByText('Edit All'));
    await flush();
    await fireEvent.click(screen.getByText('Cancel'));
    await flush();
    // After cancel, Edit All button should reappear
    expect(screen.getByText('Edit All')).toBeInTheDocument();
  });

  it('calls api.put for each speaker when Save All is clicked', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPEAKER_00', player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      if (path.includes('/transcript')) return Promise.resolve([]);
      return Promise.resolve([]);
    });
    vi.mocked(api.put).mockResolvedValue({});

    const onUpdate = vi.fn();
    render(SpeakerPanel, { props: makeProps({ onUpdate }) });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    await fireEvent.click(screen.getByText('Edit All'));
    await flush();
    await fireEvent.click(screen.getByText('Save All'));
    await flush();
    expect(api.put).toHaveBeenCalledWith('/speakers/1', expect.any(Object));
  });

  it('shows merge button when multiple speakers exist in edit mode', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPEAKER_00', player_name: null, character_name: null },
      { id: 2, diarization_label: 'SPEAKER_01', player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve([]);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      if (path.includes('/transcript')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps() });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    await fireEvent.click(screen.getByText('Edit All'));
    await flush();
    const mergeButtons = screen.getAllByText('Merge into...');
    expect(mergeButtons.length).toBe(2);
  });

  it('shows voice signature badge for speakers with signatures', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPK_00', player_name: 'Alice', character_name: 'Gandalf' },
    ];
    const roster = [
      { id: 10, player_name: 'Alice', character_name: 'Gandalf', is_active: 1 },
    ];
    const signatures = [
      { id: 1, roster_entry_id: 10, player_name: 'Alice', character_name: 'Gandalf', num_samples: 5 },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve(roster);
      if (path.includes('/voice-signatures')) return Promise.resolve(signatures);
      return Promise.resolve([]);
    });

    const { container } = render(SpeakerPanel, { props: makeProps({ hasAudio: true }) });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    const vsBadge = container.querySelector('.signature-badge');
    expect(vsBadge).toBeInTheDocument();
    expect(vsBadge?.textContent).toBe('VS');
  });

  it('shows Generate Voice Signatures button when speakers are linked to roster and hasAudio', async () => {
    const speakers = [
      { id: 1, diarization_label: 'SPK_00', player_name: 'Alice', character_name: 'Gandalf' },
    ];
    const roster = [
      { id: 10, player_name: 'Alice', character_name: 'Gandalf', is_active: 1 },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/speakers')) return Promise.resolve(speakers);
      if (path.includes('/roster')) return Promise.resolve(roster);
      if (path.includes('/voice-signatures')) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(SpeakerPanel, { props: makeProps({ hasAudio: true }) });
    await flush();
    const header = screen.getByRole('button', { name: /Speakers/ });
    await fireEvent.click(header);
    await flush();
    expect(screen.getByText('Generate Voice Signatures')).toBeInTheDocument();
  });
});
