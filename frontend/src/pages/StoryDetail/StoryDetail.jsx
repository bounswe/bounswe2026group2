import React, { useState, useEffect, useCallback } from 'react';
import StoryDetailSkeleton from '../../components/SkeletonLoader/SkeletonLoader';
import { ToastContainer, useToast } from '../../components/Toast/Toast';
import './StoryDetail.css';

/*
 * StoryDetail — /story/:id
 *
 * Requirements addressed:
 *   1.1.5.1  Authenticated users can comment
 *   1.1.5.2  Authenticated users can like
 *   1.1.5.3  Unauthenticated users can view public content
 *   1.1.5.4  Authenticated users can save for later
 *   1.2.2.3  Display preview of info associated with a marker
 *   1.2.7.3  Display created post after successful submission
 *
 * States: Loading | Success | 404 Not Found | Error
 *
 * Dependencies:
 *   - Backend GET /api/stories/:id
 *   - Map library (Issue #82)
 *   - React Router useParams for :id extraction (Issue #101)
 */

// Placeholder: replace with useParams() from react-router-dom once Issue #101 is done
const useStoryId = () => {
  const match = window.location.pathname.match(/\/story\/(\w+)/);
  return match ? match[1] : null;
};

const PLACEHOLDER_IMAGE = 'data:image/svg+xml,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" fill="%23EDE6DA">' +
  '<rect width="800" height="400"/>' +
  '<text x="400" y="210" text-anchor="middle" font-family="Georgia" font-size="18" fill="%238A7E6B">No media available</text>' +
  '</svg>'
);

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
};

const StoryDetail = () => {
  const storyId = useStoryId();
  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [liked, setLiked] = useState(false);
  const [saved, setSaved] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [comment, setComment] = useState('');
  const [comments, setComments] = useState([]);
  const [mediaError, setMediaError] = useState(false);
  const { toasts, addToast, removeToast } = useToast();

  // Fetch story data
  useEffect(() => {
    if (!storyId) {
      setNotFound(true);
      setLoading(false);
      return;
    }

    let cancelled = false;
    const fetchStory = async () => {
      try {
        const res = await fetch(`/api/stories/${storyId}`);
        if (!cancelled) {
          if (res.status === 404) {
            setNotFound(true);
          } else if (res.ok) {
            const data = await res.json();
            setStory(data);
            setLikeCount(data.like_count || 0);
            setLiked(data.user_liked || false);
            setSaved(data.user_saved || false);
            setComments(data.comments || []);
          }
        }
      } catch {
        if (!cancelled) addToast('Failed to load story.', 'error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchStory();
    return () => { cancelled = true; };
  }, [storyId]);

  // ── Like (Req 1.1.5.2) ──
  const handleLike = useCallback(async () => {
    try {
      const res = await fetch(`/api/stories/${storyId}/like`, { method: 'POST' });
      if (res.status === 401) {
        addToast('Sign in to like stories.', 'info');
        return;
      }
      if (res.ok) {
        setLiked((prev) => !prev);
        setLikeCount((prev) => liked ? prev - 1 : prev + 1);
      }
    } catch {
      addToast('Could not update like.', 'error');
    }
  }, [storyId, liked, addToast]);

  // ── Save (Req 1.1.5.4) ──
  const handleSave = useCallback(async () => {
    try {
      const res = await fetch(`/api/stories/${storyId}/save`, { method: 'POST' });
      if (res.status === 401) {
        addToast('Sign in to save stories.', 'info');
        return;
      }
      if (res.ok) {
        setSaved((prev) => !prev);
        addToast(saved ? 'Removed from saved.' : 'Story saved!', 'success');
      }
    } catch {
      addToast('Could not save story.', 'error');
    }
  }, [storyId, saved, addToast]);

  // ── Comment (Req 1.1.5.1) ──
  const handleComment = useCallback(async (e) => {
    e.preventDefault();
    if (!comment.trim()) return;

    try {
      const res = await fetch(`/api/stories/${storyId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: comment.trim() }),
      });
      if (res.status === 401) {
        addToast('Sign in to comment.', 'info');
        return;
      }
      if (res.ok) {
        const newComment = await res.json();
        setComments((prev) => [newComment, ...prev]);
        setComment('');
      }
    } catch {
      addToast('Could not post comment.', 'error');
    }
  }, [storyId, comment, addToast]);

  // ── Loading state ──
  if (loading) {
    return (
      <div className="story-detail">
        <StoryDetailSkeleton />
      </div>
    );
  }

  // ── 404 state ──
  if (notFound) {
    return (
      <div className="story-detail">
        <div className="story-detail__not-found">
          <div className="story-detail__not-found-icon">
            <svg width="72" height="72" viewBox="0 0 72 72" fill="none">
              <circle cx="36" cy="36" r="33" stroke="#C4B59A" strokeWidth="2" strokeDasharray="6 4" />
              <path d="M36 20v20M36 48v2" stroke="#C4883A" strokeWidth="3" strokeLinecap="round" />
            </svg>
          </div>
          <h2 className="story-detail__not-found-title">Story Not Found</h2>
          <p className="story-detail__not-found-text">
            This story may have been removed or the link might be incorrect.
          </p>
          <a href="/" className="story-detail__btn story-detail__btn--primary">
            Back to the Map
          </a>
        </div>
      </div>
    );
  }

  if (!story) return null;

  // ── Determine primary media ──
  const primaryMedia = story.media?.[0] || null;
  const isVideo = primaryMedia?.type?.startsWith('video/') || primaryMedia?.url?.match(/\.(mp4|webm)$/i);
  const isAudio = primaryMedia?.type?.startsWith('audio/') || primaryMedia?.url?.match(/\.(mp3|wav|ogg)$/i);

  return (
    <div className="story-detail">
      <ToastContainer toasts={toasts} removeToast={removeToast} />

      {/* ── Hero media ── */}
      <div className="story-detail__hero">
        {primaryMedia && !mediaError ? (
          isVideo ? (
            <video
              className="story-detail__hero-media"
              src={primaryMedia.url}
              controls
              poster={primaryMedia.thumbnail_url || undefined}
              onError={() => setMediaError(true)}
            />
          ) : isAudio ? (
            <div className="story-detail__hero-audio">
              <div className="story-detail__hero-audio-icon">&#9835;</div>
              <audio
                src={primaryMedia.url}
                controls
                onError={() => setMediaError(true)}
                className="story-detail__audio-player"
              />
            </div>
          ) : (
            <img
              className="story-detail__hero-media"
              src={primaryMedia.url}
              alt={story.title}
              onError={() => setMediaError(true)}
            />
          )
        ) : (
          <img
            className="story-detail__hero-media story-detail__hero-media--placeholder"
            src={PLACEHOLDER_IMAGE}
            alt="No media"
          />
        )}
        <div className="story-detail__hero-overlay" />
      </div>

      {/* ── Content column ── */}
      <article className="story-detail__content">
        {/* Meta bar */}
        <div className="story-detail__meta">
          {story.location_name && (
            <span className="story-detail__meta-location">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ verticalAlign: '-2px' }}>
                <path d="M7 1C4.52 1 2.5 3.02 2.5 5.5 2.5 8.69 7 13 7 13s4.5-4.31 4.5-7.5C11.5 3.02 9.48 1 7 1zm0 6a1.5 1.5 0 110-3 1.5 1.5 0 010 3z"
                  fill="currentColor" />
              </svg>
              {' '}{story.location_name}
            </span>
          )}
          {story.start_date && (
            <span className="story-detail__meta-date">
              {formatDate(story.start_date)}
              {story.end_date && ` \u2013 ${formatDate(story.end_date)}`}
            </span>
          )}
        </div>

        <h1 className="story-detail__title">{story.title}</h1>

        {story.author && (
          <div className="story-detail__author">
            <div className="story-detail__author-avatar">
              {story.author.username?.[0]?.toUpperCase() || '?'}
            </div>
            <div>
              <span className="story-detail__author-name">{story.author.username}</span>
              {story.created_at && (
                <span className="story-detail__author-date">
                  Posted {formatDate(story.created_at)}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Story body */}
        <div className="story-detail__body">
          {story.body.split('\n').map((paragraph, i) => (
            paragraph.trim() ? <p key={i}>{paragraph}</p> : null
          ))}
        </div>

        {/* Additional media gallery */}
        {story.media && story.media.length > 1 && (
          <div className="story-detail__gallery">
            {story.media.slice(1).map((m, i) => (
              <div key={i} className="story-detail__gallery-item">
                {m.type?.startsWith('image/') || m.url?.match(/\.(jpg|jpeg|png|webp)$/i) ? (
                  <img src={m.url} alt={`${story.title} media ${i + 2}`} className="story-detail__gallery-img" />
                ) : m.type?.startsWith('audio/') || m.url?.match(/\.(mp3|wav|ogg)$/i) ? (
                  <audio src={m.url} controls className="story-detail__gallery-audio" />
                ) : (
                  <video src={m.url} controls className="story-detail__gallery-video" />
                )}
              </div>
            ))}
          </div>
        )}

        {/* Location map (Req 1.2.2.3) */}
        {(story.latitude || story.longitude) && (
          <div className="story-detail__map-section">
            <h3 className="story-detail__section-heading">Location</h3>
            <div
              className="story-detail__map-container"
              id="story-detail-map"
              role="application"
              aria-label="Map showing story location"
            >
              <div className="story-detail__map-placeholder">
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                  <path d="M14 2C9.03 2 5 6.03 5 11c0 6.38 9 15 9 15s9-8.62 9-15c0-4.97-4.03-9-9-9zm0 12.2a3.2 3.2 0 110-6.4 3.2 3.2 0 010 6.4z"
                    fill="#C4883A" opacity="0.5" />
                </svg>
                <span>Map loading (Issue #82)</span>
              </div>
            </div>
          </div>
        )}

        {/* ── Interaction bar (Req 1.1.5.1, 1.1.5.2, 1.1.5.4) ── */}
        <div className="story-detail__actions">
          <button
            className={`story-detail__action-btn ${liked ? 'story-detail__action-btn--active' : ''}`}
            onClick={handleLike}
            aria-label={liked ? 'Unlike this story' : 'Like this story'}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill={liked ? 'currentColor' : 'none'}>
              <path d="M9 15.77l-1.17-1.06C4.1 11.4 1.5 9.07 1.5 6.19 1.5 3.86 3.36 2 5.69 2c1.31 0 2.57.61 3.31 1.57C9.74 2.61 11 2 12.31 2c2.33 0 4.19 1.86 4.19 4.19 0 2.88-2.6 5.21-6.33 8.52L9 15.77z"
                stroke="currentColor" strokeWidth="1.5" />
            </svg>
            <span>{likeCount}</span>
          </button>

          <button
            className={`story-detail__action-btn ${saved ? 'story-detail__action-btn--active' : ''}`}
            onClick={handleSave}
            aria-label={saved ? 'Remove from saved' : 'Save this story'}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill={saved ? 'currentColor' : 'none'}>
              <path d="M3.75 2.25h10.5a.75.75 0 01.75.75v13.5l-6-3.75-6 3.75V3a.75.75 0 01.75-.75z"
                stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
            <span>{saved ? 'Saved' : 'Save'}</span>
          </button>
        </div>

        {/* ── Comments (Req 1.1.5.1) ── */}
        <div className="story-detail__comments-section">
          <h3 className="story-detail__section-heading">
            Comments {comments.length > 0 && <span className="story-detail__comment-count">({comments.length})</span>}
          </h3>

          <form className="story-detail__comment-form" onSubmit={handleComment}>
            <textarea
              className="story-detail__comment-input"
              placeholder="Share your thoughts on this story..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              aria-label="Write a comment"
            />
            <button
              type="submit"
              className="story-detail__btn story-detail__btn--primary story-detail__btn--small"
              disabled={!comment.trim()}
            >
              Post Comment
            </button>
          </form>

          <div className="story-detail__comment-list">
            {comments.length === 0 && (
              <p className="story-detail__comments-empty">No comments yet. Be the first to share your thoughts.</p>
            )}
            {comments.map((c, i) => (
              <div key={c.id || i} className="story-detail__comment">
                <div className="story-detail__comment-avatar">
                  {c.author?.username?.[0]?.toUpperCase() || '?'}
                </div>
                <div className="story-detail__comment-body">
                  <div className="story-detail__comment-header">
                    <span className="story-detail__comment-author">{c.author?.username || 'Anonymous'}</span>
                    <span className="story-detail__comment-date">{formatDate(c.created_at)}</span>
                  </div>
                  <p className="story-detail__comment-text">{c.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </article>
    </div>
  );
};

export default StoryDetail;
