import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import CampaignDashboard from './CampaignDashboard.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    del: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../lib/router.svelte', () => ({
  navigate: vi.fn(),
  parseHash: vi.fn(() => ({ path: '/', params: {} })),
  matchRoute: vi.fn(),
}));

import { api } from '../lib/api';
import { navigate } from '../lib/router.svelte';

const mockCampaign = { id: 1, name: 'Test Campaign', description: 'A test', language: 'en', num_speakers: 5, session_start_number: 0, similarity_threshold: 0.65 };
const mockSessions = [
  { id: 10, name: 'Session 1', date: '2025-01-01', status: 'completed', audio_path: '/audio.wav', session_number: 1, transcript_count: 5, summary_count: 1, image_count: 2 },
  { id: 11, name: 'Session 2', date: '2025-01-08', status: 'draft', audio_path: null, session_number: 2, transcript_count: 0, summary_count: 0, image_count: 0 },
];
const mockDashboard = { session_count: 2, total_recorded_time: 7200, most_recent_session_date: '2025-01-08' };

function setupMocks() {
  vi.mocked(api.get).mockImplementation((path: string) => {
    if (path.includes('/sessions')) return Promise.resolve(mockSessions);
    if (path.includes('/dashboard')) return Promise.resolve(mockDashboard);
    return Promise.resolve(mockCampaign);
  });
}

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('CampaignDashboard', () => {
  afterEach(() => {
    cleanup();
    vi.mocked(api.get).mockReset();
  });

  it('shows loading state initially', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {})); // never resolves
    render(CampaignDashboard, { props: { campaignId: 1 } });
    expect(screen.getByText(/Loading campaign/)).toBeInTheDocument();
  });

  it('shows campaign name after loading', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Test Campaign')).toBeInTheDocument();
  });

  it('shows campaign description', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('A test')).toBeInTheDocument();
  });

  it('shows dashboard stats', async () => {
    setupMocks();
    const { container } = render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    const statCards = container.querySelectorAll('.stat-card');
    expect(statCards.length).toBe(3);
    expect(screen.getByText('2h 0m')).toBeInTheDocument(); // 7200 seconds
    expect(screen.getByText('Recorded')).toBeInTheDocument();
  });

  it('shows session cards', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Session 1')).toBeInTheDocument();
    expect(screen.getByText('Session 2')).toBeInTheDocument();
  });

  it('shows status badges on sessions', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('draft')).toBeInTheDocument();
  });

  it('shows session feature badges', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Audio')).toBeInTheDocument();
    expect(screen.getByText('Transcript')).toBeInTheDocument();
    expect(screen.getByText('Summary')).toBeInTheDocument();
    expect(screen.getByText('Images (2)')).toBeInTheDocument();
  });

  it('navigates to session on click', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Session 1'));
    expect(navigate).toHaveBeenCalledWith('/sessions/10');
  });

  it('shows "New Session" button', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('New Session')).toBeInTheDocument();
  });

  it('shows new session form when button is clicked', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('New Session'));
    expect(screen.getByText('Create')).toBeInTheDocument();
  });

  it('shows empty state when no sessions', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/sessions')) return Promise.resolve([]);
      if (path.includes('/dashboard')) return Promise.resolve({ session_count: 0, total_recorded_time: 0, most_recent_session_date: null });
      return Promise.resolve(mockCampaign);
    });
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText(/No sessions yet/)).toBeInTheDocument();
  });

  it('navigates to party page', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Party'));
    expect(navigate).toHaveBeenCalledWith('/campaigns/1/roster');
  });

  it('shows delete campaign button', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Delete Campaign')).toBeInTheDocument();
  });

  it('shows confirm dialog when Delete Campaign is clicked', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Delete Campaign'));
    expect(screen.getByText(/permanently delete/)).toBeInTheDocument();
  });

  it('creates a session when form is submitted', async () => {
    setupMocks();
    vi.mocked(api.post).mockResolvedValue({});
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('New Session'));
    await flush();
    await fireEvent.click(screen.getByText('Create'));
    await flush();
    expect(api.post).toHaveBeenCalledWith('/campaigns/1/sessions', expect.any(Object));
  });

  it('shows delete session confirm when delete button is clicked', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    const deleteButtons = screen.getAllByText('Delete');
    await fireEvent.click(deleteButtons[0]);
    expect(screen.getByText('Delete Session')).toBeInTheDocument();
  });

  it('shows Continue Last Session button when sessions exist', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Continue Last Session')).toBeInTheDocument();
  });

  it('shows Settings button', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('shows settings panel when Settings is clicked', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Settings'));
    await flush();
    expect(screen.getByText('Campaign Settings')).toBeInTheDocument();
  });

  it('shows session dates', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('2025-01-01')).toBeInTheDocument();
    // "2025-01-08" appears in both session card and dashboard Last Session stat
    const dateElements = screen.getAllByText('2025-01-08');
    expect(dateElements).toHaveLength(2);
  });

  it('shows "Start First Session" when no sessions exist', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/sessions')) return Promise.resolve([]);
      if (path.includes('/dashboard')) return Promise.resolve({ session_count: 0, total_recorded_time: 0, most_recent_session_date: null });
      return Promise.resolve(mockCampaign);
    });
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Start First Session')).toBeInTheDocument();
  });

  it('shows Voice Signature Confidence slider in settings panel', async () => {
    setupMocks();
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Settings'));
    await flush();
    expect(screen.getByText(/Voice Signature Confidence/)).toBeInTheDocument();
  });

  it('saves similarity_threshold when campaign settings are saved', async () => {
    setupMocks();
    vi.mocked(api.put).mockResolvedValue({});
    render(CampaignDashboard, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Settings'));
    await flush();
    await fireEvent.click(screen.getByText('Save'));
    await flush();
    expect(api.put).toHaveBeenCalledWith('/campaigns/1', expect.objectContaining({
      similarity_threshold: 0.65,
    }));
  });
});
