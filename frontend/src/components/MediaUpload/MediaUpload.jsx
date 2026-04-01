import React, { useRef, useState, useCallback } from 'react';
import './MediaUpload.css';

const MAX_FILE_SIZE_MB = 10;
const ACCEPTED_TYPES = {
  'image/jpeg': 'Photo',
  'image/png': 'Photo',
  'image/webp': 'Photo',
  'video/mp4': 'Video',
  'video/webm': 'Video',
  'audio/mpeg': 'Audio',
  'audio/wav': 'Audio',
  'audio/ogg': 'Audio',
};

const MediaUpload = ({ files, onChange, onError }) => {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const validateAndAdd = useCallback((newFiles) => {
    const validated = [];
    for (const file of newFiles) {
      if (!ACCEPTED_TYPES[file.type]) {
        onError?.(`"${file.name}" is not a supported format. Use photos, videos, or audio files.`);
        continue;
      }
      if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        onError?.(`"${file.name}" exceeds ${MAX_FILE_SIZE_MB}MB limit.`);
        continue;
      }
      validated.push(file);
    }
    if (validated.length > 0) {
      onChange([...files, ...validated]);
    }
  }, [files, onChange, onError]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    validateAndAdd(Array.from(e.dataTransfer.files));
  };

  const handleFileSelect = (e) => {
    validateAndAdd(Array.from(e.target.files));
    e.target.value = '';
  };

  const removeFile = (index) => {
    onChange(files.filter((_, i) => i !== index));
  };

  const getPreview = (file) => {
    if (file.type.startsWith('image/')) {
      return URL.createObjectURL(file);
    }
    return null;
  };

  const getFileIcon = (file) => {
    if (file.type.startsWith('video/')) return '\u25B6';
    if (file.type.startsWith('audio/')) return '\u266B';
    return '\u25A3';
  };

  const getFileLabel = (file) => ACCEPTED_TYPES[file.type] || 'File';

  return (
    <div className="media-upload">
      <div
        className={`media-upload__dropzone ${dragOver ? 'media-upload__dropzone--active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload media files"
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/*,video/*,audio/*"
          onChange={handleFileSelect}
          className="media-upload__input"
          aria-hidden="true"
        />
        <div className="media-upload__dropzone-content">
          <div className="media-upload__dropzone-icon">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <path d="M20 6v28M6 20h28" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>
          <p className="media-upload__dropzone-text">
            Drop photos, videos, or audio here
          </p>
          <p className="media-upload__dropzone-hint">
            or click to browse &middot; max {MAX_FILE_SIZE_MB}MB per file
          </p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="media-upload__previews">
          {files.map((file, index) => {
            const preview = getPreview(file);
            return (
              <div key={`${file.name}-${index}`} className="media-upload__preview-card">
                {preview ? (
                  <img
                    src={preview}
                    alt={`Preview of ${file.name}`}
                    className="media-upload__preview-image"
                    onLoad={() => URL.revokeObjectURL(preview)}
                  />
                ) : (
                  <div className="media-upload__preview-placeholder">
                    <span className="media-upload__preview-icon">{getFileIcon(file)}</span>
                  </div>
                )}
                <div className="media-upload__preview-info">
                  <span className="media-upload__preview-type">{getFileLabel(file)}</span>
                  <span className="media-upload__preview-name" title={file.name}>{file.name}</span>
                </div>
                <button
                  className="media-upload__preview-remove"
                  onClick={(e) => { e.stopPropagation(); removeFile(index); }}
                  aria-label={`Remove ${file.name}`}
                >
                  &times;
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default MediaUpload;
