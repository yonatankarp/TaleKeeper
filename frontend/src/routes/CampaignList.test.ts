import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import CampaignList from './CampaignList.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn().mockResolvedValue({ id: 1 }),
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

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('CampaignList', () => {
  afterEach(() => {
    cleanup();
    vi.mocked(api.get).mockReset().mockResolvedValue([]);
    vi.mocked(api.post).mockReset().mockResolvedValue({ id: 1 });
  });

  it('shows loading state initially', () => {
    render(CampaignList);
    expect(screen.getByText(/Loading campaigns/)).toBeInTheDocument();
  });

  it('shows "Campaigns" heading after loading', async () => {
    render(CampaignList);
    await flush();
    expect(screen.getByText('Campaigns')).toBeInTheDocument();
  });

  it('shows "New Campaign" button', async () => {
    render(CampaignList);
    await flush();
    expect(screen.getByText('New Campaign')).toBeInTheDocument();
  });

  it('shows empty state when no campaigns', async () => {
    render(CampaignList);
    await flush();
    expect(screen.getByText(/No campaigns yet/)).toBeInTheDocument();
  });

  it('renders campaign cards', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, name: 'Dragon Campaign', description: 'A tale of dragons', language: 'en', num_speakers: 5, session_start_number: 0, created_at: '2025-01-01' },
      { id: 2, name: 'Pirate Campaign', description: '', language: 'en', num_speakers: 4, session_start_number: 0, created_at: '2025-01-02' },
    ]);
    render(CampaignList);
    await flush();
    expect(screen.getByText('Dragon Campaign')).toBeInTheDocument();
    expect(screen.getByText('Pirate Campaign')).toBeInTheDocument();
  });

  it('shows campaign description', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, name: 'Test', description: 'Epic adventure', language: 'en', num_speakers: 5, session_start_number: 0, created_at: '2025-01-01' },
    ]);
    render(CampaignList);
    await flush();
    expect(screen.getByText('Epic adventure')).toBeInTheDocument();
  });

  it('navigates to campaign on name click', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 42, name: 'My Campaign', description: '', language: 'en', num_speakers: 5, session_start_number: 0, created_at: '2025-01-01' },
    ]);
    render(CampaignList);
    await flush();
    await fireEvent.click(screen.getByText('My Campaign'));
    expect(navigate).toHaveBeenCalledWith('/campaigns/42');
  });

  it('shows create form when "New Campaign" is clicked', async () => {
    render(CampaignList);
    await flush();
    await fireEvent.click(screen.getByText('New Campaign'));
    expect(screen.getByPlaceholderText('Campaign name')).toBeInTheDocument();
    expect(screen.getByText('Create')).toBeInTheDocument();
  });

  it('shows edit and delete buttons on campaign cards', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, name: 'Test', description: '', language: 'en', num_speakers: 5, session_start_number: 0, created_at: '2025-01-01' },
    ]);
    render(CampaignList);
    await flush();
    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('shows confirm dialog when delete is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, name: 'Test', description: '', language: 'en', num_speakers: 5, session_start_number: 0, created_at: '2025-01-01' },
    ]);
    render(CampaignList);
    await flush();
    await fireEvent.click(screen.getByText('Delete'));
    expect(screen.getByText('Delete Campaign')).toBeInTheDocument();
    expect(screen.getByText(/permanently delete/)).toBeInTheDocument();
  });

  it('calls api.post when creating a campaign', async () => {
    render(CampaignList);
    await flush();
    await fireEvent.click(screen.getByText('New Campaign'));
    const nameInput = screen.getByPlaceholderText('Campaign name');
    await fireEvent.input(nameInput, { target: { value: 'New Adventure' } });
    await fireEvent.click(screen.getByText('Create'));
    await flush();
    expect(api.post).toHaveBeenCalledWith('/campaigns', expect.objectContaining({
      name: 'New Adventure',
    }));
  });

  it('shows validation error when creating campaign with empty name', async () => {
    render(CampaignList);
    await flush();
    await fireEvent.click(screen.getByText('New Campaign'));
    await fireEvent.click(screen.getByText('Create'));
    await flush();
    expect(screen.getByText('Campaign name is required')).toBeInTheDocument();
  });

  it('shows edit form when Edit is clicked on a campaign', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, name: 'Test', description: 'Desc', language: 'en', num_speakers: 5, session_start_number: 0, created_at: '2025-01-01' },
    ]);
    render(CampaignList);
    await flush();
    await fireEvent.click(screen.getByText('Edit'));
    await flush();
    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test')).toBeInTheDocument();
  });

  it('hides create form when Cancel is clicked', async () => {
    render(CampaignList);
    await flush();
    await fireEvent.click(screen.getByText('New Campaign'));
    expect(screen.getByPlaceholderText('Campaign name')).toBeInTheDocument();
    await fireEvent.click(screen.getByText('Cancel'));
    await flush();
    expect(screen.queryByPlaceholderText('Campaign name')).not.toBeInTheDocument();
  });

  it('shows language, speakers, and session start number fields in create form', async () => {
    render(CampaignList);
    await flush();
    await fireEvent.click(screen.getByText('New Campaign'));
    await flush();
    expect(screen.getByText('Language')).toBeInTheDocument();
    expect(screen.getByText('Number of Speakers')).toBeInTheDocument();
    expect(screen.getByText('First session number')).toBeInTheDocument();
  });
});
