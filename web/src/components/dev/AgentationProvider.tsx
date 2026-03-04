'use client';

import dynamic from 'next/dynamic';

const AgentationLazy = dynamic(
  () => import('agentation').then((m) => ({ default: m.Agentation })),
  { ssr: false },
);

export default function AgentationProvider() {
  if (process.env.NODE_ENV !== 'development') return null;
  return <AgentationLazy />;
}
