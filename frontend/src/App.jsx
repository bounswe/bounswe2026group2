import React, { useState } from 'react';
import StoryCreate from './pages/StoryCreate/StoryCreate';
import StoryDetail from './pages/StoryDetail/StoryDetail';

const MOCK_STORY = {
  id: '1',
  title: 'The Old Fisherman\u2019s Quarter of Kadik\u00f6y',
  body: `In the narrow streets behind the bustling Kadik\u00f6y market, there once stood a row of wooden houses where fishermen mended their nets each evening. My grandfather was one of them.\n\nEvery morning before dawn, he would walk down to the pier with his worn leather bag, the smell of salt thick in the air. The neighborhood cats knew his schedule better than he did \u2014 they\u2019d line up along the dock, waiting for the scraps he always saved.\n\nBy the 1980s, most of the wooden houses had been replaced by concrete apartments. But if you walk through the back streets today, you can still find the old stone fountain where the fishermen used to wash their catch. The inscription on it reads 1923.`,
  location_name: 'Kadik\u00f6y, Istanbul',
  latitude: 40.9903,
  longitude: 29.0291,
  start_date: '1965-01-01',
  end_date: '1985-12-31',
  created_at: '2026-03-28T14:30:00Z',
  like_count: 12,
  user_liked: false,
  user_saved: false,
  author: { username: 'mehmet_arif' },
  media: [
    { url: 'https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=800&h=480&fit=crop', type: 'image/jpeg' },
    { url: 'https://images.unsplash.com/photo-1527838832700-5059252407fa?w=400&h=300&fit=crop', type: 'image/jpeg' },
    { url: 'https://images.unsplash.com/photo-1569396116180-210c182bedb8?w=400&h=300&fit=crop', type: 'image/jpeg' },
  ],
  comments: [
    {
      id: 'c1',
      author: { username: 'ayse_k' },
      text: 'My grandmother used to live in that neighborhood! She always talked about the fishermen and the cats. Thank you for sharing this.',
      created_at: '2026-03-28T16:00:00Z',
    },
    {
      id: 'c2',
      author: { username: 'can_photo' },
      text: 'I photographed that fountain last year. The inscription is barely readable now but it\u2019s still there. Beautiful piece of history.',
      created_at: '2026-03-29T09:15:00Z',
    },
  ],
};

/* Preview app — toggle between StoryCreate and StoryDetail */
const App = () => {
  const [page, setPage] = useState('create');

  return (
    <div>
      {/* Preview navigation bar */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 99999,
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '8px 16px',
        background: '#1A1A1A', color: '#FAF6F0',
        fontFamily: "'Source Sans 3', sans-serif", fontSize: '0.85rem',
        boxShadow: '0 2px 12px rgba(0,0,0,0.3)',
      }}>
        <span style={{ fontWeight: 700, marginRight: 12, opacity: 0.6, letterSpacing: '0.06em', textTransform: 'uppercase', fontSize: '0.75rem' }}>
          Preview
        </span>
        <button
          onClick={() => setPage('create')}
          style={{
            padding: '5px 14px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: page === 'create' ? '#C4883A' : 'rgba(255,255,255,0.1)',
            color: '#FAF6F0', fontWeight: page === 'create' ? 600 : 400,
            fontSize: '0.85rem',
          }}
        >
          Story Create (Issue #105)
        </button>
        <button
          onClick={() => setPage('detail')}
          style={{
            padding: '5px 14px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: page === 'detail' ? '#C4883A' : 'rgba(255,255,255,0.1)',
            color: '#FAF6F0', fontWeight: page === 'detail' ? 600 : 400,
            fontSize: '0.85rem',
          }}
        >
          Story Detail (Issue #114)
        </button>
        <button
          onClick={() => setPage('detail-404')}
          style={{
            padding: '5px 14px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: page === 'detail-404' ? '#C4883A' : 'rgba(255,255,255,0.1)',
            color: '#FAF6F0', fontWeight: page === 'detail-404' ? 600 : 400,
            fontSize: '0.85rem',
          }}
        >
          404 State
        </button>
        <button
          onClick={() => setPage('detail-loading')}
          style={{
            padding: '5px 14px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: page === 'detail-loading' ? '#C4883A' : 'rgba(255,255,255,0.1)',
            color: '#FAF6F0', fontWeight: page === 'detail-loading' ? 600 : 400,
            fontSize: '0.85rem',
          }}
        >
          Loading State
        </button>
      </nav>

      <div style={{ paddingTop: 44 }}>
        {page === 'create' && <StoryCreate />}
        {page === 'detail' && <MockStoryDetail story={MOCK_STORY} />}
        {page === 'detail-404' && <MockStoryDetail story={null} notFound />}
        {page === 'detail-loading' && <MockStoryDetail story={null} loading />}
      </div>
    </div>
  );
};

/*
 * MockStoryDetail wraps StoryDetail with mock data so we can preview
 * without a real backend. It intercepts fetch calls.
 */
const MockStoryDetail = ({ story, notFound, loading }) => {
  React.useEffect(() => {
    const originalFetch = window.fetch;
    window.fetch = async (url, opts) => {
      // Intercept story fetch
      if (typeof url === 'string' && url.match(/\/api\/stories\/\w+$/) && (!opts || opts.method !== 'POST')) {
        if (loading) {
          return new Promise(() => {}); // never resolves — loading forever
        }
        if (notFound) {
          return { ok: false, status: 404, json: async () => ({ detail: 'Not found' }) };
        }
        return { ok: true, status: 200, json: async () => story };
      }
      // Intercept like
      if (typeof url === 'string' && url.includes('/like')) {
        return { ok: true, status: 200, json: async () => ({}) };
      }
      // Intercept save
      if (typeof url === 'string' && url.includes('/save')) {
        return { ok: true, status: 200, json: async () => ({}) };
      }
      // Intercept comments
      if (typeof url === 'string' && url.includes('/comments')) {
        const body = opts?.body ? JSON.parse(opts.body) : {};
        return {
          ok: true, status: 200,
          json: async () => ({
            id: 'c' + Date.now(),
            author: { username: 'you' },
            text: body.text,
            created_at: new Date().toISOString(),
          }),
        };
      }
      return originalFetch(url, opts);
    };

    // Set URL so StoryDetail can extract the ID
    if (!notFound && !loading && story) {
      window.history.replaceState(null, '', `/story/${story.id}`);
    } else {
      window.history.replaceState(null, '', '/story/unknown');
    }

    return () => { window.fetch = originalFetch; };
  }, [story, notFound, loading]);

  return <StoryDetail key={`${notFound}-${loading}`} />;
};

export default App;
