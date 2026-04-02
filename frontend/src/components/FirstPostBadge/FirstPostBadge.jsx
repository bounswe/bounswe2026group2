import React, { useState, useEffect } from 'react';
import './FirstPostBadge.css';

const FirstPostBadge = ({ show, onDismiss }) => {
  const [animating, setAnimating] = useState(false);

  useEffect(() => {
    if (show) {
      requestAnimationFrame(() => setAnimating(true));
    }
  }, [show]);

  if (!show) return null;

  return (
    <div className={`first-post-badge-overlay ${animating ? 'first-post-badge-overlay--visible' : ''}`}>
      <div className="first-post-badge">
        <div className="first-post-badge__glow" />
        <div className="first-post-badge__icon">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="28" stroke="#C4883A" strokeWidth="2.5" fill="rgba(196,136,58,0.08)" />
            <path d="M32 16l4.5 9.1 10 1.5-7.25 7.1 1.7 10-8.95-4.7-8.95 4.7 1.7-10-7.25-7.1 10-1.5L32 16z"
              fill="#C4883A" stroke="#C4883A" strokeWidth="1" />
          </svg>
        </div>
        <h3 className="first-post-badge__title">First Story Published!</h3>
        <p className="first-post-badge__subtitle">
          You've earned the <strong>Pioneer Storyteller</strong> badge for sharing your first piece of local history.
        </p>
        <button className="first-post-badge__button" onClick={onDismiss}>
          Continue Exploring
        </button>
      </div>
    </div>
  );
};

export default FirstPostBadge;
