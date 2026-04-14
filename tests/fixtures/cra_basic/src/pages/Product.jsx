import React from 'react';
import { Helmet } from 'react-helmet-async';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

function Product() {
  const { id } = useParams();
  const { data } = useQuery({
    queryKey: ['product', id],
    queryFn: () => fetch(`/api/product/${id}`).then(r => r.json()),
  });

  return (
    <>
      <Helmet>
        <title>{data?.name || 'Product'}</title>
        <meta name="description" content={data?.description || ''} />
      </Helmet>
      <h1>{data?.name}</h1>
    </>
  );
}

export default Product;
