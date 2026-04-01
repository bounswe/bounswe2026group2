import React, { useState, useCallback, useRef } from 'react';
import MediaUpload from '../../components/MediaUpload/MediaUpload';
import FirstPostBadge from '../../components/FirstPostBadge/FirstPostBadge';
import { ToastContainer, useToast } from '../../components/Toast/Toast';
import './StoryCreate.css';

/*
 * StoryCreate — /create-story
 *
 * Requirements addressed:
 *   1.1.1.1  Upload photos, videos, audio from device
 *   1.1.2.1  Drag/interact with map to pin location
 *   1.1.3.1  Create post via button on main page (this is the destination)
 *     .1     Select location during post creation
 *     .2     Choose specific time during post creation
 *     .3     Specify time range for post
 *     .4     Create text content
 *   1.1.3.2  Upload post after completing required fields
 *   1.1.3.3  See success page after posting
 *   1.2.1.1  In-app audio/video recording
 *   1.2.1.1.1  Audio transcription shown for review
 *   1.2.3.2  First Post badge display
 *   1.2.7.2  Required field validation before submission
 *   2.2.4.1  File size validation on upload
 *
 * Content types (from scenarios):
 *   - Write Text (req 1.1.3.1.4)
 *   - Add Photos (req 1.1.1.1, scenario 1)
 *   - Record / Upload Audio (req 1.2.1.1, scenario 3)
 *   - Add Video (req 1.1.1.1)
 *
 * Dependencies:
 *   - MediaUpload component (Issue #102)
 *   - Backend POST /api/stories endpoint
 *   - Map library (Issue #82 — map API selection pending)
 */

const MAX_FILE_SIZE_MB = 10;

const INITIAL_FORM = {
  title: '',
  body: '',
  locationName: '',
  latitude: null,
  longitude: null,
  dateType: 'specific',   // 'specific' | 'range'
  startDate: '',
  endDate: '',
  photos: [],
  videos: [],
  audioFiles: [],
  recording: null,        // in-app recorded audio blob
  transcription: '',      // auto-transcribed text from recording (req 1.2.1.1.1)
};

/* Reusable drop zone for a specific file type */
const FileDropZone = ({ accept, hint, files, onAdd, onRemove, renderPreview }) => {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  return (
    <div className="story-create__dropzone-wrapper">
      <div
        className={`story-create__mini-dropzone ${dragOver ? 'story-create__mini-dropzone--active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); onAdd(Array.from(e.dataTransfer.files)); }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={accept}
          onChange={(e) => { onAdd(Array.from(e.target.files)); e.target.value = ''; }}
          style={{ display: 'none' }}
        />
        <span className="story-create__mini-dropzone-text">{hint}</span>
      </div>
      {files.length > 0 && (
        <div className="story-create__file-list">
          {files.map((file, i) => (
            <div key={`${file.name}-${i}`} className="story-create__file-item">
              {renderPreview(file)}
              <button type="button" className="story-create__remove-btn" onClick={() => onRemove(i)}>&times;</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const StoryCreate = () => {
  const [form, setForm] = useState(INITIAL_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [showBadge, setShowBadge] = useState(false);
  const [createdStory, setCreatedStory] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const { toasts, addToast, removeToast } = useToast();

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  // ── File helpers ──
  const addFiles = (field, acceptedTypes, newFiles) => {
    const validated = [];
    for (const file of newFiles) {
      if (!acceptedTypes.some((t) => file.type.startsWith(t))) {
        addToast(`"${file.name}" is not the correct format for this section.`, 'error');
        continue;
      }
      if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        addToast(`"${file.name}" exceeds ${MAX_FILE_SIZE_MB}MB limit.`, 'error');
        continue;
      }
      validated.push(file);
    }
    if (validated.length > 0) {
      setForm((prev) => ({ ...prev, [field]: [...prev[field], ...validated] }));
    }
  };

  const removeFile = (field, index) => {
    setForm((prev) => ({ ...prev, [field]: prev[field].filter((_, i) => i !== index) }));
  };

  // ── In-app audio recording (Req 1.2.1.1) ──
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        updateField('recording', blob);
        stream.getTracks().forEach((t) => t.stop());
        // Placeholder: in production, send blob to speech-to-text service
        // and set transcription (Req 1.2.1.1.1)
        updateField('transcription', '[Transcription will appear here after processing]');
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      addToast('Microphone access denied. Please allow microphone permissions.', 'error');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const removeRecording = () => {
    updateField('recording', null);
    updateField('transcription', '');
  };

  const validate = () => {
    const errors = [];
    if (!form.title.trim()) errors.push('Title is required.');
    if (!form.body.trim() && !form.recording) errors.push('Story text or a voice recording is required.');
    if (!form.locationName.trim() && !form.latitude) errors.push('Location is required.');
    if (!form.startDate) errors.push('Start date is required.');
    if (form.dateType === 'range' && !form.endDate) errors.push('End date is required for a date range.');
    if (form.dateType === 'range' && form.startDate && form.endDate && form.endDate < form.startDate) {
      errors.push('End date must be after start date.');
    }
    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errors = validate();
    if (errors.length > 0) {
      errors.forEach((err) => addToast(err, 'error'));
      return;
    }

    setSubmitting(true);

    try {
      const payload = new FormData();
      payload.append('title', form.title.trim());
      payload.append('body', form.body.trim());
      payload.append('location_name', form.locationName.trim());
      if (form.latitude != null) payload.append('latitude', form.latitude);
      if (form.longitude != null) payload.append('longitude', form.longitude);
      payload.append('start_date', form.startDate);
      if (form.dateType === 'range' && form.endDate) payload.append('end_date', form.endDate);
      form.photos.forEach((file) => payload.append('photos', file));
      form.videos.forEach((file) => payload.append('videos', file));
      form.audioFiles.forEach((file) => payload.append('audio', file));
      if (form.recording) payload.append('recording', form.recording, 'recording.webm');
      if (form.transcription) payload.append('transcription', form.transcription);

      const response = await fetch('/api/stories', {
        method: 'POST',
        body: payload,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => null);
        if (response.status === 400 && err?.detail) {
          const details = Array.isArray(err.detail) ? err.detail : [err.detail];
          details.forEach((d) => addToast(typeof d === 'string' ? d : d.msg || 'Validation error', 'error'));
        } else {
          addToast('Something went wrong. Please try again.', 'error');
        }
        return;
      }

      const data = await response.json();
      setCreatedStory(data);
      setSubmitted(true);
      addToast('Your story has been published!', 'success');

      if (data.is_first_post) {
        setShowBadge(true);
      }
    } catch {
      addToast('Network error. Check your connection and try again.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Success state (Req 1.1.3.3) ──
  if (submitted && createdStory) {
    return (
      <div className="story-create">
        <ToastContainer toasts={toasts} removeToast={removeToast} />
        <FirstPostBadge show={showBadge} onDismiss={() => setShowBadge(false)} />
        <div className="story-create__success">
          <div className="story-create__success-icon">
            <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
              <circle cx="28" cy="28" r="26" stroke="#3A7D5C" strokeWidth="2.5" fill="rgba(58,125,92,0.06)" />
              <path d="M18 28.5l7 7 13-14" stroke="#3A7D5C" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h2 className="story-create__success-title">Story Published</h2>
          <p className="story-create__success-text">
            Your story <em>"{createdStory.title}"</em> is now live and pinned to the map.
          </p>
          <div className="story-create__success-actions">
            {/* These links will work once routing from Issue #101 is in place */}
            <a href={`/story/${createdStory.id}`} className="story-create__btn story-create__btn--primary">
              View Your Story
            </a>
            <a href="/" className="story-create__btn story-create__btn--secondary">
              Back to Map
            </a>
          </div>
        </div>
      </div>
    );
  }

  // ── Creation form ──
  return (
    <div className="story-create">
      <ToastContainer toasts={toasts} removeToast={removeToast} />

      <header className="story-create__header">
        <span className="story-create__header-label">New Story</span>
        <h1 className="story-create__heading">Share a Piece of History</h1>
        <p className="story-create__subheading">
          Pin a personal story to a place on the map. Add photos, audio, or video to bring it to life.
        </p>
      </header>

      <form className="story-create__form" onSubmit={handleSubmit} noValidate>
        {/* ── Title ── */}
        <div className="story-create__field">
          <label htmlFor="story-title" className="story-create__label">
            Title <span className="story-create__required">*</span>
          </label>
          <input
            id="story-title"
            type="text"
            className="story-create__input story-create__input--title"
            placeholder="Give your story a name..."
            value={form.title}
            onChange={(e) => updateField('title', e.target.value)}
            maxLength={200}
            autoFocus
          />
        </div>

        {/* ── Content Type Buttons (from scenarios) ── */}
        <div className="story-create__field" style={{ gridColumn: '1 / -1' }}>
          <label className="story-create__label">Add Content</label>
          <p className="story-create__field-hint">
            Tell your story using text, photos, audio, or video.
          </p>
          <div className="story-create__content-types">
            {/* ── Write Text (Req 1.1.3.1.4) ── */}
            <div className="story-create__content-block">
              <div className="story-create__content-block-header">
                <span className="story-create__content-icon story-create__content-icon--text">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M3 4h14M3 8h10M3 12h12M3 16h8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </span>
                <span className="story-create__content-type-label">Write Text</span>
              </div>
              <input
                id="story-body"
                type="text"
                className="story-create__input"
                placeholder="Tell the story behind this place..."
                value={form.body}
                onChange={(e) => updateField('body', e.target.value)}
              />
            </div>

            {/* ── Add Photos (Req 1.1.1.1, scenario 1) ── */}
            <div className="story-create__content-block">
              <div className="story-create__content-block-header">
                <span className="story-create__content-icon story-create__content-icon--photo">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <rect x="2" y="3" width="16" height="14" rx="2" stroke="currentColor" strokeWidth="1.6" />
                    <circle cx="7" cy="8" r="2" stroke="currentColor" strokeWidth="1.4" />
                    <path d="M2 14l4-4 3 3 4-5 5 6" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
                  </svg>
                </span>
                <span className="story-create__content-type-label">Add Photos</span>
              </div>
              <FileDropZone
                accept="image/*"
                hint="Drop photos here or click to browse"
                files={form.photos}
                onAdd={(files) => addFiles('photos', ['image/'], files)}
                onRemove={(i) => removeFile('photos', i)}
                renderPreview={(file) => (
                  <img src={URL.createObjectURL(file)} alt={file.name} className="story-create__thumb" />
                )}
              />
            </div>

            {/* ── Record / Upload Audio (Req 1.2.1.1, scenario 3) ── */}
            <div className="story-create__content-block">
              <div className="story-create__content-block-header">
                <span className="story-create__content-icon story-create__content-icon--audio">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <rect x="7" y="2" width="6" height="10" rx="3" stroke="currentColor" strokeWidth="1.6" />
                    <path d="M4 10a6 6 0 0012 0M10 16v2M7 18h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                  </svg>
                </span>
                <span className="story-create__content-type-label">Record a Story</span>
              </div>

              <FileDropZone
                accept="audio/*"
                hint="Drop audio files here or click to browse"
                files={form.audioFiles}
                onAdd={(files) => addFiles('audioFiles', ['audio/'], files)}
                onRemove={(i) => removeFile('audioFiles', i)}
                renderPreview={(file) => (
                  <div className="story-create__file-badge">
                    <span className="story-create__file-badge-icon">&#9835;</span>
                    <span className="story-create__file-badge-name">{file.name}</span>
                  </div>
                )}
              />
            </div>

            {/* ── Add Video (Req 1.1.1.1) ── */}
            <div className="story-create__content-block">
              <div className="story-create__content-block-header">
                <span className="story-create__content-icon story-create__content-icon--video">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <rect x="2" y="4" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.6" />
                    <path d="M14 8l4-2v8l-4-2" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                  </svg>
                </span>
                <span className="story-create__content-type-label">Add Video</span>
              </div>
              <FileDropZone
                accept="video/*"
                hint="Drop video files here or click to browse"
                files={form.videos}
                onAdd={(files) => addFiles('videos', ['video/'], files)}
                onRemove={(i) => removeFile('videos', i)}
                renderPreview={(file) => (
                  <div className="story-create__file-badge">
                    <span className="story-create__file-badge-icon">&#9654;</span>
                    <span className="story-create__file-badge-name">{file.name}</span>
                  </div>
                )}
              />
            </div>
          </div>
        </div>

        {/* ── Location (Req 1.1.2.1, 1.1.3.1.1) ── */}
        <div className="story-create__field">
          <label className="story-create__label">
            Location <span className="story-create__required">*</span>
          </label>
          <p className="story-create__field-hint">
            Search for a place or drag the pin on the map.
          </p>
          <input
            id="story-location"
            type="text"
            className="story-create__input"
            placeholder="Search for a place..."
            value={form.locationName}
            onChange={(e) => updateField('locationName', e.target.value)}
            aria-label="Search location by name"
          />
          {/* Map container — will be initialized by map library (Issue #82) */}
          <div
            className="story-create__map-container"
            id="story-create-map"
            role="application"
            aria-label="Interactive map for selecting story location"
          >
            <div className="story-create__map-placeholder">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <path d="M16 3C10.48 3 6 7.48 6 13c0 7.25 10 16 10 16s10-8.75 10-16c0-5.52-4.48-10-10-10zm0 13.5a3.5 3.5 0 110-7 3.5 3.5 0 010 7z"
                  fill="#C4883A" opacity="0.5" />
              </svg>
              <span>Map will load here</span>
              <span className="story-create__map-placeholder-sub">Requires map API integration (Issue #82)</span>
            </div>
          </div>
          {form.latitude && form.longitude && (
            <p className="story-create__coords">
              {form.latitude.toFixed(5)}, {form.longitude.toFixed(5)}
            </p>
          )}
        </div>

        {/* ── Date / Time (Req 1.1.3.1.2, 1.1.3.1.3) ── */}
        <div className="story-create__field">
          <label className="story-create__label">
            When did this happen? <span className="story-create__required">*</span>
          </label>
          <div className="story-create__date-row">
            <div className="story-create__date-type-toggle">
              <button
                type="button"
                className={`story-create__toggle-btn ${form.dateType === 'specific' ? 'story-create__toggle-btn--active' : ''}`}
                onClick={() => updateField('dateType', 'specific')}
              >
                Specific Date
              </button>
              <button
                type="button"
                className={`story-create__toggle-btn ${form.dateType === 'range' ? 'story-create__toggle-btn--active' : ''}`}
                onClick={() => updateField('dateType', 'range')}
              >
                Date Range
              </button>
            </div>
            <button type="button" className="story-create__ai-btn" title="Let AI estimate the date from your story content.">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 0C8 4.4 4.4 8 0 8c4.4 0 8 3.6 8 8 0-4.4 3.6-8 8-8-4.4 0-8-3.6-8-8z" fill="currentColor" />
              </svg>
              Unsure?
            </button>
          </div>
          <div className="story-create__date-inputs">
            <div className="story-create__date-field">
              <label htmlFor="story-start-date" className="story-create__date-label">
                {form.dateType === 'range' ? 'From' : 'Date'}
              </label>
              <input
                id="story-start-date"
                type="date"
                className="story-create__input"
                value={form.startDate}
                onChange={(e) => updateField('startDate', e.target.value)}
              />
            </div>
            {form.dateType === 'range' && (
              <div className="story-create__date-field">
                <label htmlFor="story-end-date" className="story-create__date-label">To</label>
                <input
                  id="story-end-date"
                  type="date"
                  className="story-create__input"
                  value={form.endDate}
                  onChange={(e) => updateField('endDate', e.target.value)}
                />
              </div>
            )}
          </div>
        </div>

        {/* ── Submit (Req 1.1.3.2) ── */}
        <div className="story-create__submit-bar">
          <a href="/" className="story-create__btn story-create__btn--ghost">Cancel</a>
          <button
            type="submit"
            className="story-create__btn story-create__btn--primary"
            disabled={submitting}
          >
            {submitting ? (
              <span className="story-create__spinner" />
            ) : (
              'Publish Story'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default StoryCreate;
