'use client';

import { lazy, Suspense, useState, useEffect } from 'react';

export default function AgentationProvider() {
  if (process.env.NODE_ENV !== 'development') return null;
  return <AgentationLoader />;
}

function AgentationLoader() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  const AgentationLazy = lazy(() =>
    import('agentation').then((m) => ({ default: m.Agentation }))
  );

  return (
    <Suspense fallback={null}>
      <AgentationLazy />
    </Suspense>
  );
}
