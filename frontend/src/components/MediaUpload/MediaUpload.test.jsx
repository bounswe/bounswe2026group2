import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import MediaUpload from './MediaUpload';

const createFile = (name, type, sizeMB = 1) => {
  const file = new File(['x'.repeat(sizeMB * 1024 * 1024)], name, { type });
  return file;
};

describe('MediaUpload', () => {
  it('renders the dropzone', () => {
    render(<MediaUpload files={[]} onChange={() => {}} />);
    expect(screen.getByText(/Drop photos, videos, or audio here/)).toBeInTheDocument();
    expect(screen.getByLabelText('Upload media files')).toBeInTheDocument();
  });

  it('rejects unsupported file types and calls onError', () => {
    const onChange = vi.fn();
    const onError = vi.fn();

    render(<MediaUpload files={[]} onChange={onChange} onError={onError} />);

    const dropzone = screen.getByLabelText('Upload media files');
    const badFile = createFile('doc.pdf', 'application/pdf', 1);

    // Simulate drop since userEvent.upload doesn't preserve file.type in jsdom
    const dataTransfer = { files: [badFile] };
    dropzone.dispatchEvent(new Event('dragover', { bubbles: true }));
    const dropEvent = new Event('drop', { bubbles: true });
    Object.defineProperty(dropEvent, 'dataTransfer', { value: dataTransfer });
    dropEvent.preventDefault = vi.fn();
    dropzone.dispatchEvent(dropEvent);

    expect(onError).toHaveBeenCalledWith(expect.stringContaining('not a supported format'));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('rejects files exceeding 10MB and calls onError', async () => {
    const onChange = vi.fn();
    const onError = vi.fn();
    const user = userEvent.setup();

    render(<MediaUpload files={[]} onChange={onChange} onError={onError} />);

    const input = document.querySelector('input[type="file"]');
    const bigFile = createFile('huge.jpg', 'image/jpeg', 11);

    await user.upload(input, bigFile);

    expect(onError).toHaveBeenCalledWith(expect.stringContaining('exceeds'));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('accepts valid files and calls onChange', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<MediaUpload files={[]} onChange={onChange} />);

    const input = document.querySelector('input[type="file"]');
    const validFile = createFile('photo.jpg', 'image/jpeg', 1);

    await user.upload(input, validFile);

    expect(onChange).toHaveBeenCalledWith([validFile]);
  });

  it('renders file previews and remove buttons', async () => {
    const onChange = vi.fn();
    const files = [createFile('song.mp3', 'audio/mpeg', 1)];
    const user = userEvent.setup();

    render(<MediaUpload files={files} onChange={onChange} />);

    expect(screen.getByText('song.mp3')).toBeInTheDocument();
    expect(screen.getByText('Audio')).toBeInTheDocument();

    await user.click(screen.getByLabelText('Remove song.mp3'));
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
