import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import LanguageSelect from './LanguageSelect.svelte';

describe('LanguageSelect', () => {
  afterEach(() => cleanup());

  function makeProps(overrides = {}) {
    return {
      value: 'en',
      onchange: vi.fn(),
      ...overrides,
    };
  }

  it('renders with the selected language name as placeholder', () => {
    render(LanguageSelect, { props: makeProps({ value: 'en' }) });
    const input = screen.getByPlaceholderText('English');
    expect(input).toBeInTheDocument();
  });

  it('opens dropdown on focus', async () => {
    const { container } = render(LanguageSelect, { props: makeProps() });
    const input = screen.getByPlaceholderText('English');
    await fireEvent.focus(input);
    const dropdown = container.querySelector('.dropdown');
    expect(dropdown).toBeInTheDocument();
  });

  it('filters languages when typing', async () => {
    const { container } = render(LanguageSelect, { props: makeProps() });
    const input = screen.getByPlaceholderText('English');
    await fireEvent.focus(input);
    await fireEvent.input(input, { target: { value: 'French' } });
    const options = container.querySelectorAll('.option');
    expect(options.length).toBeGreaterThan(0);
    const texts = Array.from(options).map((o) => o.textContent);
    expect(texts.some((t) => t?.includes('French'))).toBe(true);
    expect(texts.some((t) => t?.includes('Japanese'))).toBe(false);
  });

  it('shows "No languages found" for non-matching search', async () => {
    render(LanguageSelect, { props: makeProps() });
    const input = screen.getByPlaceholderText('English');
    await fireEvent.focus(input);
    await fireEvent.input(input, { target: { value: 'zzzznotlang' } });
    expect(screen.getByText('No languages found')).toBeInTheDocument();
  });

  it('calls onchange when a language is selected', async () => {
    const onchange = vi.fn();
    const { container } = render(LanguageSelect, { props: makeProps({ onchange }) });
    const input = screen.getByPlaceholderText('English');
    await fireEvent.focus(input);
    await fireEvent.input(input, { target: { value: 'French' } });
    const option = container.querySelector('.option');
    expect(option).toBeTruthy();
    await fireEvent.mouseDown(option!);
    expect(onchange).toHaveBeenCalledWith('fr');
  });

  it('closes dropdown on blur', async () => {
    vi.useFakeTimers();
    const { container } = render(LanguageSelect, { props: makeProps() });
    const input = screen.getByPlaceholderText('English');
    await fireEvent.focus(input);
    expect(container.querySelector('.dropdown')).toBeInTheDocument();
    await fireEvent.blur(input);
    expect(container.querySelector('.dropdown')).toBeInTheDocument();
    await vi.advanceTimersByTimeAsync(150);
    expect(container.querySelector('.dropdown')).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it('applies compact class when compact prop is true', () => {
    const { container } = render(LanguageSelect, { props: makeProps({ compact: true }) });
    const wrapper = container.querySelector('.lang-select');
    expect(wrapper?.classList.contains('compact')).toBe(true);
  });

  it('does not apply compact class when compact prop is false', () => {
    const { container } = render(LanguageSelect, { props: makeProps({ compact: false }) });
    const wrapper = container.querySelector('.lang-select');
    expect(wrapper?.classList.contains('compact')).toBe(false);
  });

  it('keyboard: Escape closes the dropdown', async () => {
    const { container } = render(LanguageSelect, { props: makeProps() });
    const input = screen.getByPlaceholderText('English');
    await fireEvent.focus(input);
    expect(container.querySelector('.dropdown')).toBeInTheDocument();
    await fireEvent.keyDown(input, { key: 'Escape' });
    expect(container.querySelector('.dropdown')).not.toBeInTheDocument();
  });
});
