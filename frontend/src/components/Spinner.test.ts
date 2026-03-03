import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import Spinner from './Spinner.svelte';

describe('Spinner', () => {
  it('renders a spinner element', () => {
    const { container } = render(Spinner);
    const spinner = container.querySelector('.spinner');
    expect(spinner).toBeInTheDocument();
  });

  it('uses default size of 24px', () => {
    const { container } = render(Spinner);
    const spinner = container.querySelector('.spinner') as HTMLElement;
    expect(spinner.style.width).toBe('24px');
    expect(spinner.style.height).toBe('24px');
  });

  it('accepts a custom size prop', () => {
    const { container } = render(Spinner, { props: { size: '48px' } });
    const spinner = container.querySelector('.spinner') as HTMLElement;
    expect(spinner.style.width).toBe('48px');
    expect(spinner.style.height).toBe('48px');
  });

  it('renders as a span element', () => {
    const { container } = render(Spinner);
    const spinner = container.querySelector('.spinner');
    expect(spinner?.tagName).toBe('SPAN');
  });
});
