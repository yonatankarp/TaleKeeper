import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import TranscriptView from './TranscriptView.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
  reDiarize: vi.fn(),
}));

import { api } from '../lib/api';

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('TranscriptView', () => {
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
      ...overrides,
    };
  }

  it('shows "No transcript available" when no segments and not recording', async () => {
    render(TranscriptView, { props: makeProps() });
    await flush();
    expect(
      screen.getByText('No transcript available. Start recording or retranscribe audio to generate one.'),
    ).toBeInTheDocument();
  });

  it('shows "Waiting for speech..." when isRecording is true and no segments', async () => {
    render(TranscriptView, { props: makeProps({ isRecording: true }) });
    await flush();
    expect(screen.getByText('Waiting for speech...')).toBeInTheDocument();
  });

  it('renders segments when API returns data', async () => {
    const segments = [
      { id: 1, text: 'Hello, adventurers!', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
      { id: 2, text: 'Roll for initiative.', start_time: 5, end_time: 10, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });

    render(TranscriptView, { props: makeProps() });
    await flush();
    expect(screen.getByText('Hello, adventurers!')).toBeInTheDocument();
    expect(screen.getByText('Roll for initiative.')).toBeInTheDocument();
  });

  it('shows search bar when segments exist', async () => {
    const segments = [
      { id: 1, text: 'Some transcript text', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });

    render(TranscriptView, { props: makeProps() });
    await flush();
    expect(screen.getByPlaceholderText('Search transcript...')).toBeInTheDocument();
  });

  it('formats timestamps correctly', async () => {
    const segments = [
      { id: 1, text: 'After one hour', start_time: 3661, end_time: 3665, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });

    render(TranscriptView, { props: makeProps() });
    await flush();
    expect(screen.getByText('01:01:01')).toBeInTheDocument();
  });

  it('shows speaker labels when present', async () => {
    const segments = [
      { id: 1, text: 'I cast fireball!', start_time: 10, end_time: 15, speaker_id: 1, diarization_label: 'SPEAKER_00', player_name: 'Alice', character_name: 'Gandalf' },
      { id: 2, text: 'I dodge.', start_time: 15, end_time: 18, speaker_id: 2, diarization_label: 'SPEAKER_01', player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });

    render(TranscriptView, { props: makeProps() });
    await flush();
    expect(screen.getByText('Gandalf (Alice)')).toBeInTheDocument();
    expect(screen.getByText('SPEAKER_01')).toBeInTheDocument();
  });

  it('shows processing banner when status is audio_ready', async () => {
    render(TranscriptView, { props: makeProps({ status: 'audio_ready', hasAudio: true }) });
    await flush();
    expect(screen.getByText(/Processing audio/)).toBeInTheDocument();
  });

  it('shows processing banner with preview note when segments exist and status is audio_ready', async () => {
    const segments = [
      { id: 1, text: 'Preview text', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });

    const { container } = render(TranscriptView, { props: makeProps({ status: 'audio_ready', hasAudio: true }) });
    await flush();
    const banner = container.querySelector('.processing-banner');
    expect(banner).toBeInTheDocument();
    expect(banner?.textContent).toContain('preview');
  });

  it('shows download button when segments exist', async () => {
    const segments = [
      { id: 1, text: 'Test', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });

    const { container } = render(TranscriptView, { props: makeProps() });
    await flush();
    const downloadBtn = container.querySelector('.download-btn');
    expect(downloadBtn).toBeInTheDocument();
  });

  it('filters segments with search', async () => {
    const segments = [
      { id: 1, text: 'Hello world', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
      { id: 2, text: 'Goodbye moon', start_time: 5, end_time: 10, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });

    render(TranscriptView, { props: makeProps() });
    await flush();
    const searchInput = screen.getByPlaceholderText('Search transcript...');
    await fireEvent.input(searchInput, { target: { value: 'Hello' } });
    await flush();
    expect(screen.getByText('Hello world')).toBeInTheDocument();
    expect(screen.getByText('1 matches')).toBeInTheDocument();
  });

  it('shows character name only when player name is missing', async () => {
    const segments = [
      { id: 1, text: 'Test', start_time: 0, end_time: 5, speaker_id: 1, diarization_label: 'SPK', player_name: null, character_name: 'Gandalf' },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      return Promise.resolve([]);
    });

    render(TranscriptView, { props: makeProps() });
    await flush();
    expect(screen.getByText('Gandalf')).toBeInTheDocument();
  });

  it('shows player name only when character name is missing', async () => {
    const segments = [
      { id: 1, text: 'Test', start_time: 0, end_time: 5, speaker_id: 1, diarization_label: 'SPK', player_name: 'Alice', character_name: null },
    ];

    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      return Promise.resolve([]);
    });

    render(TranscriptView, { props: makeProps() });
    await flush();
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });

  it('shows retranscribe bar when hasAudio and status is completed', async () => {
    render(TranscriptView, { props: makeProps({ hasAudio: true, status: 'completed' }) });
    await flush();
    expect(screen.getByText('Retranscribe')).toBeInTheDocument();
    expect(screen.getByText('Re-diarize')).toBeInTheDocument();
  });

  it('does not show retranscribe bar when status is audio_ready', async () => {
    render(TranscriptView, { props: makeProps({ hasAudio: true, status: 'audio_ready' }) });
    await flush();
    expect(screen.queryByText('Retranscribe')).not.toBeInTheDocument();
  });

  it('shows time hint when status is audio_ready', async () => {
    render(TranscriptView, { props: makeProps({ hasAudio: true, status: 'audio_ready' }) });
    await flush();
    expect(screen.getByText(/Transcription may take a few minutes/)).toBeInTheDocument();
  });

  it('shows "Processing audio" banner when status is audio_ready and no segments', async () => {
    render(TranscriptView, { props: makeProps({ status: 'audio_ready', hasAudio: true }) });
    await flush();
    expect(screen.getByText(/Processing audio/)).toBeInTheDocument();
  });

  it('shows download button with download icon', async () => {
    const segments = [
      { id: 1, text: 'Test', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });
    const { container } = render(TranscriptView, { props: makeProps() });
    await flush();
    const downloadBtn = container.querySelector('.download-btn');
    expect(downloadBtn).toBeInTheDocument();
  });

  it('shows copy button on each segment', async () => {
    const segments = [
      { id: 1, text: 'Hello', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });
    const { container } = render(TranscriptView, { props: makeProps() });
    await flush();
    const copyBtns = container.querySelectorAll('.copy-btn');
    expect(copyBtns.length).toBe(1);
  });

  it('shows "No matches found" when search has no results', async () => {
    const segments = [
      { id: 1, text: 'Hello world', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });
    render(TranscriptView, { props: makeProps() });
    await flush();
    const searchInput = screen.getByPlaceholderText('Search transcript...');
    await fireEvent.input(searchInput, { target: { value: 'zzzznotfound' } });
    await flush();
    expect(screen.getByText('No matches found.')).toBeInTheDocument();
  });

  it('shows clear button when searching', async () => {
    const segments = [
      { id: 1, text: 'Hello world', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });
    render(TranscriptView, { props: makeProps() });
    await flush();
    const searchInput = screen.getByPlaceholderText('Search transcript...');
    await fireEvent.input(searchInput, { target: { value: 'Hello' } });
    await flush();
    expect(screen.getByText('Clear')).toBeInTheDocument();
  });

  it('clears search when clear button is clicked', async () => {
    const segments = [
      { id: 1, text: 'Hello world', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
      { id: 2, text: 'Goodbye moon', start_time: 5, end_time: 10, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      if (path.includes('/campaigns/')) return Promise.resolve({ num_speakers: 5 });
      return Promise.resolve([]);
    });
    render(TranscriptView, { props: makeProps() });
    await flush();
    const searchInput = screen.getByPlaceholderText('Search transcript...');
    await fireEvent.input(searchInput, { target: { value: 'Hello' } });
    await flush();
    await fireEvent.click(screen.getByText('Clear'));
    await flush();
    expect(screen.getByText('Hello world')).toBeInTheDocument();
    expect(screen.getByText('Goodbye moon')).toBeInTheDocument();
  });

  it('shows speakers label with retranscribe bar', async () => {
    render(TranscriptView, { props: makeProps({ hasAudio: true, status: 'completed' }) });
    await flush();
    expect(screen.getByText('Speakers')).toBeInTheDocument();
  });

  it('shows diarization label when only diarization_label is set', async () => {
    const segments = [
      { id: 1, text: 'Test', start_time: 0, end_time: 5, speaker_id: 1, diarization_label: 'SPEAKER_00', player_name: null, character_name: null },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      return Promise.resolve([]);
    });
    render(TranscriptView, { props: makeProps() });
    await flush();
    expect(screen.getByText('SPEAKER_00')).toBeInTheDocument();
  });

  it('shows no speaker label when segment has no speaker info', async () => {
    const segments = [
      { id: 1, text: 'Unnamed', start_time: 0, end_time: 5, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      return Promise.resolve([]);
    });
    const { container } = render(TranscriptView, { props: makeProps() });
    await flush();
    const speakerLabels = container.querySelectorAll('.speaker');
    expect(speakerLabels.length).toBe(0);
  });

  it('makes segments clickable when hasAudio is true', async () => {
    const segments = [
      { id: 1, text: 'Click me', start_time: 10, end_time: 15, speaker_id: null, diarization_label: null, player_name: null, character_name: null },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/transcript')) return Promise.resolve([...segments]);
      return Promise.resolve([]);
    });
    const { container } = render(TranscriptView, { props: makeProps({ hasAudio: true }) });
    await flush();
    const clickableSegment = container.querySelector('.segment.clickable');
    expect(clickableSegment).toBeInTheDocument();
  });
});
