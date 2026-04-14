import React from 'react';
import { BrowserRouter, useRoutes } from 'react-router-dom';

function Home() {
  return <h1>Home</h1>;
}

function Docs() {
  return <h1>Docs</h1>;
}

function AppRoutes() {
  return useRoutes([
    { path: '/', element: <Home /> },
    { path: '/docs/:slug', element: <Docs /> },
  ]);
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
