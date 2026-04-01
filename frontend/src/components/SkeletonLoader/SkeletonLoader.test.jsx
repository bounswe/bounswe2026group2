import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { SkeletonBlock, StoryDetailSkeleton } from './SkeletonLoader';

describe('SkeletonBlock', () => {
  it('renders with default dimensions', () => {
    const { container } = render(<SkeletonBlock />);
    const block = container.firstChild;
    expect(block).toHaveStyle({ width: '100%', height: '1em', borderRadius: '6px' });
  });

  it('renders with custom dimensions', () => {
    const { container } = render(<SkeletonBlock width="50%" height="2rem" radius="12px" />);
    const block = container.firstChild;
    expect(block).toHaveStyle({ width: '50%', height: '2rem', borderRadius: '12px' });
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonBlock className="my-class" />);
    expect(container.firstChild).toHaveClass('skeleton-block', 'my-class');
  });
});

describe('StoryDetailSkeleton', () => {
  it('renders the skeleton layout', () => {
    const { container } = render(<StoryDetailSkeleton />);
    expect(container.querySelector('.skeleton-story-detail')).toBeInTheDocument();
    expect(container.querySelector('.skeleton-story-detail__hero')).toBeInTheDocument();
    expect(container.querySelector('.skeleton-story-detail__body')).toBeInTheDocument();
    expect(container.querySelector('.skeleton-story-detail__map')).toBeInTheDocument();
  });
});
