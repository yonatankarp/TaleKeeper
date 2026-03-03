import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import RosterPage from './RosterPage.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    del: vi.fn().mockResolvedValue({}),
  },
}));

import { api } from '../lib/api';

const mockRoster = [
  { id: 1, player_name: 'Alice', character_name: 'Gandalf', description: 'A wizard', sheet_url: '', sheet_data: '', is_active: 1 },
  { id: 2, player_name: 'Bob', character_name: 'Aragorn', description: '', sheet_url: '', sheet_data: '', is_active: 1 },
  { id: 3, player_name: 'Carol', character_name: 'Legolas', description: '', sheet_url: '', sheet_data: '', is_active: 0 },
];

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('RosterPage', () => {
  afterEach(() => {
    cleanup();
    vi.mocked(api.get).mockReset().mockResolvedValue([]);
    vi.mocked(api.post).mockReset().mockResolvedValue({});
    vi.mocked(api.put).mockReset().mockResolvedValue({});
    vi.mocked(api.del).mockReset().mockResolvedValue({});
  });

  it('shows loading state initially', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    render(RosterPage, { props: { campaignId: 1 } });
    expect(screen.getByText(/Loading party/)).toBeInTheDocument();
  });

  it('shows "Party" heading after loading', async () => {
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Party')).toBeInTheDocument();
  });

  it('shows empty state when no entries', async () => {
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText(/No players in the party yet/)).toBeInTheDocument();
  });

  it('shows add form with player and character inputs', async () => {
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByPlaceholderText('Player name')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Character name')).toBeInTheDocument();
    expect(screen.getByText('Add')).toBeInTheDocument();
  });

  it('renders roster entries', async () => {
    vi.mocked(api.get).mockResolvedValue(mockRoster);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Gandalf')).toBeInTheDocument();
    expect(screen.getByText('(Alice)')).toBeInTheDocument();
    expect(screen.getByText('Aragorn')).toBeInTheDocument();
    expect(screen.getByText('(Bob)')).toBeInTheDocument();
  });

  it('shows character description', async () => {
    vi.mocked(api.get).mockResolvedValue(mockRoster);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('A wizard')).toBeInTheDocument();
  });

  it('shows inactive badge for inactive entries', async () => {
    vi.mocked(api.get).mockResolvedValue(mockRoster);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Inactive')).toBeInTheDocument();
  });

  it('shows edit, deactivate, and remove buttons', async () => {
    vi.mocked(api.get).mockResolvedValue([mockRoster[0]]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByText('Deactivate')).toBeInTheDocument();
    expect(screen.getByText('Remove')).toBeInTheDocument();
  });

  it('shows activate button for inactive entries', async () => {
    vi.mocked(api.get).mockResolvedValue([mockRoster[2]]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Activate')).toBeInTheDocument();
  });

  it('shows confirm dialog when remove is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue([mockRoster[0]]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Remove'));
    expect(screen.getByText('Remove Party Member')).toBeInTheDocument();
  });

  it('shows upload and import buttons', async () => {
    vi.mocked(api.get).mockResolvedValue([mockRoster[0]]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Upload PDF')).toBeInTheDocument();
    expect(screen.getByText('Import URL')).toBeInTheDocument();
  });

  it('calls api.post when Add is clicked with valid input', async () => {
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    const playerInput = screen.getByPlaceholderText('Player name');
    const charInput = screen.getByPlaceholderText('Character name');
    await fireEvent.input(playerInput, { target: { value: 'Dave' } });
    await fireEvent.input(charInput, { target: { value: 'Gandalf' } });
    await fireEvent.click(screen.getByText('Add'));
    await flush();
    expect(api.post).toHaveBeenCalledWith('/campaigns/1/roster', expect.objectContaining({
      player_name: 'Dave',
      character_name: 'Gandalf',
    }));
  });

  it('does not call api.post when Add is clicked with empty inputs', async () => {
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Add'));
    await flush();
    expect(api.post).not.toHaveBeenCalled();
  });

  it('shows edit form when Edit is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue([mockRoster[0]]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Edit'));
    await flush();
    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('calls api.put when Deactivate is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue([mockRoster[0]]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Deactivate'));
    await flush();
    expect(api.put).toHaveBeenCalledWith('/roster/1', { is_active: false });
  });

  it('calls api.del when Remove is confirmed', async () => {
    vi.mocked(api.get).mockResolvedValue([mockRoster[0]]);
    const { container } = render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Remove'));
    // The confirm dialog has a btn-danger button with text "Remove"
    const confirmBtn = container.querySelector('.dialog .btn-danger') as HTMLButtonElement;
    await fireEvent.click(confirmBtn);
    await flush();
    expect(api.del).toHaveBeenCalledWith('/roster/1');
  });

  it('shows Import URL input when Import URL button is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue([mockRoster[0]]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Import URL'));
    await flush();
    expect(screen.getByPlaceholderText(/dndbeyond/)).toBeInTheDocument();
    expect(screen.getByText('Go')).toBeInTheDocument();
  });

  it('shows Refresh button for entries with sheet data', async () => {
    const entryWithSheet = { ...mockRoster[0], sheet_data: 'some data' };
    vi.mocked(api.get).mockResolvedValue([entryWithSheet]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });

  it('shows sheet source for entries with sheet_url', async () => {
    const entryWithUrl = { ...mockRoster[0], sheet_url: 'https://example.com/sheet' };
    vi.mocked(api.get).mockResolvedValue([entryWithUrl]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText(/Source:/)).toBeInTheDocument();
  });

  it('shows uploaded PDF source for entries with sheet_data only', async () => {
    const entryWithData = { ...mockRoster[0], sheet_data: 'data', sheet_url: '' };
    vi.mocked(api.get).mockResolvedValue([entryWithData]);
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByText('Source: uploaded PDF')).toBeInTheDocument();
  });

  it('shows description input in add form', async () => {
    render(RosterPage, { props: { campaignId: 1 } });
    await flush();
    expect(screen.getByPlaceholderText(/Character description/)).toBeInTheDocument();
  });
});
