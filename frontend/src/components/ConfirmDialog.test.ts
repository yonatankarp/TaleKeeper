import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import ConfirmDialog from './ConfirmDialog.svelte';

describe('ConfirmDialog', () => {
  afterEach(() => cleanup());

  function makeProps(overrides = {}) {
    return {
      title: 'Delete Item',
      message: 'Are you sure you want to delete this?',
      onconfirm: vi.fn(),
      oncancel: vi.fn(),
      ...overrides,
    };
  }

  it('renders the title', () => {
    render(ConfirmDialog, { props: makeProps() });
    expect(screen.getByText('Delete Item')).toBeInTheDocument();
  });

  it('renders the message', () => {
    render(ConfirmDialog, { props: makeProps() });
    expect(screen.getByText('Are you sure you want to delete this?')).toBeInTheDocument();
  });

  it('uses default button labels', () => {
    render(ConfirmDialog, { props: makeProps() });
    expect(screen.getByText('Confirm')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('uses custom button labels', () => {
    render(ConfirmDialog, {
      props: makeProps({ confirmLabel: 'Yes, Delete', cancelLabel: 'No, Keep' }),
    });
    expect(screen.getByText('Yes, Delete')).toBeInTheDocument();
    expect(screen.getByText('No, Keep')).toBeInTheDocument();
  });

  it('calls onconfirm when confirm button is clicked', async () => {
    const onconfirm = vi.fn();
    render(ConfirmDialog, { props: makeProps({ onconfirm }) });
    await fireEvent.click(screen.getByText('Confirm'));
    expect(onconfirm).toHaveBeenCalledOnce();
  });

  it('calls oncancel when cancel button is clicked', async () => {
    const oncancel = vi.fn();
    render(ConfirmDialog, { props: makeProps({ oncancel }) });
    await fireEvent.click(screen.getByText('Cancel'));
    expect(oncancel).toHaveBeenCalledOnce();
  });

  it('calls oncancel when Escape key is pressed', async () => {
    const oncancel = vi.fn();
    render(ConfirmDialog, { props: makeProps({ oncancel }) });
    await fireEvent.keyDown(window, { key: 'Escape' });
    expect(oncancel).toHaveBeenCalledOnce();
  });

  it('calls oncancel when backdrop is clicked', async () => {
    const oncancel = vi.fn();
    const { container } = render(ConfirmDialog, { props: makeProps({ oncancel }) });
    const backdrop = container.querySelector('.backdrop') as HTMLElement;
    await fireEvent.click(backdrop);
    expect(oncancel).toHaveBeenCalledOnce();
  });

  it('does not call oncancel when dialog content is clicked', async () => {
    const oncancel = vi.fn();
    const { container } = render(ConfirmDialog, { props: makeProps({ oncancel }) });
    const dialog = container.querySelector('.dialog') as HTMLElement;
    await fireEvent.click(dialog);
    expect(oncancel).not.toHaveBeenCalled();
  });

  it('renders the confirm button with btn-danger class', () => {
    const { container } = render(ConfirmDialog, { props: makeProps() });
    const confirmBtn = container.querySelector('.btn-danger');
    expect(confirmBtn).toBeInTheDocument();
    expect(confirmBtn?.textContent).toBe('Confirm');
  });
});
