import React from 'react';
import { Helmet } from 'react-helmet-async';
import { useQuery } from '@tanstack/react-query';

function Home() {
  const { data } = useQuery({ queryKey: ['posts'], queryFn: () => fetch('/api/posts').then(r => r.json()) });

  return (
    <>
      <Helmet>
        <title>Home Page</title>
        <meta name="description" content="Welcome to our home page" />
        <meta property="og:title" content="Home Page" />
      </Helmet>
      <h1>Welcome</h1>
      <p>{data?.length ?? 0}</p>
    </>
  );
}

export default Home;
