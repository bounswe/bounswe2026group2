import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import StoryCreate from './pages/StoryCreate/StoryCreate';
import StoryDetail from './pages/StoryDetail/StoryDetail';

const App = () => (
  <Routes>
    <Route path="/create-story" element={<StoryCreate />} />
    <Route path="/story/:storyId" element={<StoryDetail />} />
    <Route path="*" element={<Navigate to="/create-story" replace />} />
  </Routes>
);

export default App;
