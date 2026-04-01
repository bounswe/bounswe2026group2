import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import FirstPostBadge from './FirstPostBadge';

describe('FirstPostBadge', () => {
  it('renders nothing when show is false', () => {
    const { container } = render(<FirstPostBadge show={false} onDismiss={() => {}} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders badge content when show is true', () => {
    render(<FirstPostBadge show={true} onDismiss={() => {}} />);
    expect(screen.getByText('First Story Published!')).toBeInTheDocument();
    expect(screen.getByText('Pioneer Storyteller')).toBeInTheDocument();
    expect(screen.getByText('Continue Exploring')).toBeInTheDocument();
  });

  it('calls onDismiss when button is clicked', async () => {
    const onDismiss = vi.fn();
    const user = userEvent.setup();

    render(<FirstPostBadge show={true} onDismiss={onDismiss} />);
    await user.click(screen.getByText('Continue Exploring'));

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
