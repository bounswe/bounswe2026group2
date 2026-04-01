import React from 'react';
import './SkeletonLoader.css';

const SkeletonBlock = ({ width = '100%', height = '1em', radius = '6px', className = '' }) => (
  <div
    className={`skeleton-block ${className}`}
    style={{ width, height, borderRadius: radius }}
  />
);

const StoryDetailSkeleton = () => (
  <div className="skeleton-story-detail">
    <SkeletonBlock height="360px" radius="16px" className="skeleton-story-detail__hero" />
    <div className="skeleton-story-detail__body">
      <SkeletonBlock width="70%" height="2.2rem" radius="8px" />
      <div className="skeleton-story-detail__meta">
        <SkeletonBlock width="140px" height="0.9rem" />
        <SkeletonBlock width="100px" height="0.9rem" />
      </div>
      <div className="skeleton-story-detail__content">
        <SkeletonBlock width="100%" height="1rem" />
        <SkeletonBlock width="95%" height="1rem" />
        <SkeletonBlock width="88%" height="1rem" />
        <SkeletonBlock width="100%" height="1rem" />
        <SkeletonBlock width="72%" height="1rem" />
      </div>
      <SkeletonBlock height="200px" radius="12px" className="skeleton-story-detail__map" />
    </div>
  </div>
);

export { SkeletonBlock, StoryDetailSkeleton };
export default StoryDetailSkeleton;
