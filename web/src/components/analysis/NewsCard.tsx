'use client';

import { useState } from 'react';
import { Newspaper, ExternalLink } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui';
import type { NewsArticle } from '@/lib/types';

interface NewsCardProps {
  articles?: NewsArticle[];
  sentimentSummary?: string;
  onLoadNews?: () => void;
  isLoading?: boolean;
  className?: string;
}

function getSentimentBadge(sentiment: string): { label: string; className: string } {
  const s = sentiment.toLowerCase();
  if (s === 'positive' || s === 'bullish') {
    return { label: sentiment, className: 'bg-green-500/15 text-green-500' };
  }
  if (s === 'negative' || s === 'bearish') {
    return { label: sentiment, className: 'bg-red-500/15 text-red-500' };
  }
  return { label: sentiment, className: 'bg-[var(--foreground-muted)]/15 text-[var(--foreground-muted)]' };
}

function formatNewsDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffH = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffH < 1) return 'Just now';
    if (diffH < 24) return `${diffH}h ago`;
    const diffD = Math.floor(diffH / 24);
    if (diffD < 7) return `${diffD}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

export default function NewsCard({
  articles,
  sentimentSummary,
  onLoadNews,
  isLoading = false,
  className = '',
}: NewsCardProps) {
  const t = useTranslations('news');
  const [expanded, setExpanded] = useState(false);

  const hasArticles = articles && articles.length > 0;
  const displayedArticles = hasArticles
    ? (expanded ? articles : articles.slice(0, 5))
    : [];

  return (
    <div className={`rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-5 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Newspaper className="h-4 w-4 text-[var(--foreground-muted)]" />
          <h3 className="text-base font-semibold text-[var(--foreground)]">{t('title')}</h3>
        </div>
        {sentimentSummary && (
          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
            getSentimentBadge(sentimentSummary).className
          }`}>
            {sentimentSummary}
          </span>
        )}
      </div>

      {!hasArticles && onLoadNews && (
        <div className="flex flex-col items-center py-6 gap-3">
          <p className="text-sm text-[var(--foreground-muted)]">{t('loadPrompt')}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={onLoadNews}
            isLoading={isLoading}
          >
            {t('loadButton')}
          </Button>
        </div>
      )}

      {!hasArticles && !onLoadNews && (
        <p className="text-sm text-[var(--foreground-muted)] text-center py-4">{t('noArticles')}</p>
      )}

      {hasArticles && (
        <div className="space-y-3">
          {displayedArticles.map((article, i) => {
            const badge = getSentimentBadge(article.sentiment);
            return (
              <div key={i} className="flex gap-3 group">
                <div className="flex-1 min-w-0">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-[var(--foreground)] hover:text-[var(--color-primary)] transition-colors line-clamp-2 inline-flex items-center gap-1"
                  >
                    {article.title}
                    <ExternalLink className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </a>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-[var(--foreground-muted)]">{article.source}</span>
                    <span className="text-xs text-[var(--foreground-muted)]">{formatNewsDate(article.date)}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${badge.className}`}>
                      {badge.label}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
          {articles.length > 5 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-[var(--color-primary)] hover:underline"
            >
              {expanded ? t('showLess') : t('showMore', { count: articles.length - 5 })}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
