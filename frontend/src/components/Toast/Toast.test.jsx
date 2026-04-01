import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import Toast, { ToastContainer, useToast } from './Toast';

describe('Toast', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('renders message and correct icon for each type', () => {
    const { rerender } = render(<Toast message="Error occurred" type="error" onClose={() => {}} />);
    expect(screen.getByText('Error occurred')).toBeInTheDocument();
    expect(screen.getByText('!')).toBeInTheDocument();

    rerender(<Toast message="Done" type="success" onClose={() => {}} />);
    expect(screen.getByText('✓')).toBeInTheDocument();

    rerender(<Toast message="Info" type="info" onClose={() => {}} />);
    expect(screen.getByText('i')).toBeInTheDocument();
  });

  it('auto-dismisses after duration', () => {
    const onClose = vi.fn();
    render(<Toast message="Bye" duration={2000} onClose={onClose} />);

    act(() => { vi.advanceTimersByTime(2000); });
    act(() => { vi.advanceTimersByTime(300); });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when close button is clicked', async () => {
    const onClose = vi.fn();
    vi.useRealTimers();
    const user = userEvent.setup();

    render(<Toast message="Close me" onClose={onClose} />);
    await user.click(screen.getByText('×'));

    // Wait for the 300ms animation delay
    await vi.waitFor(() => expect(onClose).toHaveBeenCalled());
  });
});

describe('ToastContainer', () => {
  it('renders multiple toasts', () => {
    const toasts = [
      { id: 1, message: 'First', type: 'error' },
      { id: 2, message: 'Second', type: 'success' },
    ];
    render(<ToastContainer toasts={toasts} removeToast={() => {}} />);
    expect(screen.getByText('First')).toBeInTheDocument();
    expect(screen.getByText('Second')).toBeInTheDocument();
  });
});
