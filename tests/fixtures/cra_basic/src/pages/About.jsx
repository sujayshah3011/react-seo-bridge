import React from 'react';
import { Helmet } from 'react-helmet-async';

function About() {
  return (
    <>
      <Helmet>
        <title>About Us</title>
        <meta name="description" content="Learn about our company" />
      </Helmet>
      <h1>About</h1>
      <img src="/team.jpg" alt="Team photo" />
    </>
  );
}

export default About;
