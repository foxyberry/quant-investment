'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { RefreshCw, Send, Loader2, Clock, BookOpen, ChevronRight } from 'lucide-react';
import { listReports, getLatestReport, streamGenerateReport, sendReportToSlack } from '@/lib/api';
import type { ReportSummary, ReportDetail } from '@/lib/types';
import type { ChatStreamEvent } from '@/lib/api';

// ── Markdown renderer (reused from ChatPanel pattern) ─────────────────────────

function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n');
  const result: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];
  let tableRows: string[][] = [];
  let tableHeader: string[] | null = null;
  let nodeKey = 0;

  const flushList = () => {
    if (listItems.length > 0) {
      result.push(
        <ul key={`ul-${nodeKey++}`} className="my-1.5 ml-4 list-disc space-y-0.5 text-sm">
          {listItems}
        </ul>
      );
      listItems = [];
    }
  };

  const flushTable = () => {
    if (tableHeader && tableRows.length > 0) {
      result.push(
        <div key={`tbl-${nodeKey++}`} className="my-2 overflow-x-auto rounded-lg border border-white/10">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 bg-white/5">
                {tableHeader.map((h, i) => (
                  <th key={i} className="px-3 py-2 text-left font-semibold text-slate-200">{h.trim()}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableRows.map((row, ri) => (
                <tr key={ri} className="border-b border-white/5 hover:bg-white/5">
                  {row.map((cell, ci) => (
                    <td key={ci} className="px-3 py-1.5 text-slate-300">{inlineMarkdown(cell.trim())}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    tableHeader = null;
    tableRows = [];
  };

  const inlineMarkdown = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**'))
        return <strong key={i} className="font-semibold text-slate-100">{part.slice(2, -2)}</strong>;
      if (part.startsWith('*') && part.endsWith('*'))
        return <em key={i} className="italic">{part.slice(1, -1)}</em>;
      if (part.startsWith('`') && part.endsWith('`'))
        return <code key={i} className="rounded bg-white/10 px-1 py-0.5 font-mono text-xs text-blue-300">{part.slice(1, -1)}</code>;
      return part;
    });
  };

  for (const line of lines) {
    // Heading 2
    if (line.startsWith('## ')) {
      flushList(); flushTable();
      result.push(
        <h2 key={`h2-${nodeKey++}`} className="mt-5 mb-2 text-base font-bold text-white border-b border-white/10 pb-1">
          {inlineMarkdown(line.slice(3))}
        </h2>
      );
      continue;
    }
    // Heading 3
    if (line.startsWith('### ')) {
      flushList(); flushTable();
      result.push(
        <h3 key={`h3-${nodeKey++}`} className="mt-4 mb-1.5 text-sm font-semibold text-slate-200">
          {inlineMarkdown(line.slice(4))}
        </h3>
      );
      continue;
    }
    // Heading 4
    if (line.startsWith('#### ')) {
      flushList(); flushTable();
      result.push(
        <h4 key={`h4-${nodeKey++}`} className="mt-3 mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
          {inlineMarkdown(line.slice(5))}
        </h4>
      );
      continue;
    }
    // HR
    if (/^---+$/.test(line.trim())) {
      flushList(); flushTable();
      result.push(<hr key={`hr-${nodeKey++}`} className="my-3 border-white/10" />);
      continue;
    }
    // Blockquote
    if (line.startsWith('> ')) {
      flushList(); flushTable();
      result.push(
        <blockquote key={`bq-${nodeKey++}`} className="my-1.5 border-l-2 border-blue-500 pl-3 text-xs italic text-slate-400">
          {inlineMarkdown(line.slice(2))}
        </blockquote>
      );
      continue;
    }
    // Table header
    if (line.startsWith('|') && line.endsWith('|')) {
      const cells = line.slice(1, -1).split('|');
      if (/^[\s|:-]+$/.test(line)) {
        // separator row — skip
        continue;
      }
      flushList();
      if (tableHeader === null) {
        tableHeader = cells;
      } else {
        tableRows.push(cells);
      }
      continue;
    }
    // List item
    if (/^[-*]\s/.test(line)) {
      flushTable();
      const content = line.replace(/^[-*]\s/, '');
      listItems.push(
        <li key={`li-${nodeKey++}`} className="text-xs text-slate-300">
          {inlineMarkdown(content)}
        </li>
      );
      continue;
    }
    // Empty line
    if (line.trim() === '') {
      flushList(); flushTable();
      result.push(<div key={`sp-${nodeKey++}`} className="h-2" />);
      continue;
    }
    // Regular paragraph
    flushList(); flushTable();
    result.push(
      <p key={`p-${nodeKey++}`} className="text-xs leading-relaxed text-slate-300">
        {inlineMarkdown(line)}
      </p>
    );
  }

  flushList();
  flushTable();
  return result;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatKST(isoString: string): string {
  try {
    const d = new Date(isoString + (isoString.endsWith('Z') ? '' : 'Z'));
    return d.toLocaleString('ko-KR', {
      timeZone: 'Asia/Seoul',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

function isToday(isoString: string): boolean {
  try {
    const d = new Date(isoString + (isoString.endsWith('Z') ? '' : 'Z'));
    const now = new Date();
    return d.toDateString() === now.toDateString();
  } catch {
    return false;
  }
}

// ── Main page component ───────────────────────────────────────────────────────

export default function DailyReportPage() {
  const t = useTranslations('dailyReport');

  const [currentReport, setCurrentReport] = useState<ReportDetail | null>(null);
  const [history, setHistory] = useState<ReportSummary[]>([]);
  const [streamingContent, setStreamingContent] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [slackStatus, setSlackStatus] = useState<'idle' | 'sending' | 'sent' | 'failed'>('idle');
  const [activeTools, setActiveTools] = useState<string[]>([]);

  const abortRef = useRef<AbortController | null>(null);

  // Load latest report and history on mount
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [latest, summaries] = await Promise.all([
        getLatestReport(),
        listReports(20),
      ]);
      setCurrentReport(latest);
      setHistory(summaries);
    } catch (e: unknown) {
      setLoadError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Auto-generate if no report today
  useEffect(() => {
    if (!isLoading && !currentReport) {
      void generateReport();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading]);

  const generateReport = useCallback(async () => {
    if (isGenerating) return;
    setIsGenerating(true);
    setGenerateError(null);
    setStreamingContent('');
    setActiveTools([]);
    setSlackStatus('idle');

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      for await (const event of streamGenerateReport(abort.signal)) {
        const ev = event as ChatStreamEvent;
        if (ev.type === 'text') {
          setStreamingContent((prev) => prev + (ev as { type: 'text'; content: string }).content);
        } else if (ev.type === 'tool_start') {
          const te = ev as { type: 'tool_start'; name: string };
          setActiveTools((prev) => [...prev, te.name]);
        } else if (ev.type === 'tool_end') {
          const te = ev as { type: 'tool_end'; name: string };
          setActiveTools((prev) => prev.filter((n) => n !== te.name));
        } else if (ev.type === 'done') {
          break;
        } else if (ev.type === 'error') {
          const ee = ev as { type: 'error'; message: string };
          setGenerateError(ee.message);
          break;
        }
      }
      // Reload to get saved DB record
      await loadData();
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        setGenerateError(e.message);
      }
    } finally {
      setIsGenerating(false);
      setStreamingContent('');
      setActiveTools([]);
      abortRef.current = null;
    }
  }, [isGenerating, loadData]);

  const handleSlack = async () => {
    if (!currentReport || slackStatus === 'sending') return;
    setSlackStatus('sending');
    try {
      const ok = await sendReportToSlack(currentReport.id);
      setSlackStatus(ok ? 'sent' : 'failed');
    } catch {
      setSlackStatus('failed');
    }
  };

  const selectReport = async (id: number) => {
    if (isGenerating) return;
    try {
      const detail = await (await import('@/lib/api')).getReport(id);
      if (detail) setCurrentReport(detail);
    } catch { /* ignore */ }
  };

  const displayedContent = isGenerating && streamingContent
    ? streamingContent
    : currentReport?.content ?? '';

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar: history ── */}
      <aside className="hidden w-64 flex-shrink-0 border-r border-white/10 bg-[#0d1117] lg:flex lg:flex-col">
        <div className="border-b border-white/10 px-4 py-4">
          <h2 className="text-sm font-semibold text-slate-300">{t('history')}</h2>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          {history.length === 0 && !isLoading && (
            <p className="px-4 py-3 text-xs text-slate-500">{t('noReport')}</p>
          )}
          {history.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => void selectReport(r.id)}
              className={`w-full px-4 py-3 text-left transition-colors hover:bg-white/5 ${
                currentReport?.id === r.id ? 'bg-white/10' : ''
              }`}
            >
              <div className="flex items-center justify-between gap-1">
                <span className="text-[11px] font-medium text-slate-200 truncate">
                  {formatKST(r.generated_at)}
                </span>
                {isToday(r.generated_at) && (
                  <span className="flex-shrink-0 rounded bg-blue-600/30 px-1 py-0.5 text-[9px] font-semibold text-blue-300">
                    TODAY
                  </span>
                )}
              </div>
              <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-slate-500">
                <span>{r.trigger === 'scheduled' ? t('trigger_scheduled') : t('trigger_manual')}</span>
                {r.duration_sec != null && (
                  <>
                    <span>·</span>
                    <span>{Math.round(r.duration_sec)}s</span>
                  </>
                )}
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex flex-shrink-0 items-center justify-between border-b border-white/10 bg-[#0d1117] px-6 py-4">
          <div className="flex items-center gap-3">
            <BookOpen className="h-5 w-5 text-blue-400" />
            <div>
              <h1 className="text-base font-semibold text-white">{t('title')}</h1>
              <p className="text-xs text-slate-500">{t('subtitle')}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {currentReport && (
              <button
                type="button"
                onClick={() => void handleSlack()}
                disabled={slackStatus === 'sending' || slackStatus === 'sent'}
                className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:bg-white/10 disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5" />
                {slackStatus === 'sending'
                  ? '...'
                  : slackStatus === 'sent'
                  ? t('sent')
                  : slackStatus === 'failed'
                  ? t('sendFailed')
                  : t('sendToSlack')}
              </button>
            )}
            <button
              type="button"
              onClick={() => void generateReport()}
              disabled={isGenerating}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
            >
              {isGenerating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              {isGenerating ? t('generating') : t('generate')}
            </button>
          </div>
        </header>

        {/* Active tools indicator */}
        {activeTools.length > 0 && (
          <div className="flex flex-shrink-0 items-center gap-2 border-b border-white/5 bg-blue-950/30 px-6 py-2">
            <Loader2 className="h-3 w-3 animate-spin text-blue-400" />
            <span className="text-[11px] text-blue-300">
              {activeTools.map((name) => (
                <span key={name} className="mr-2 inline-flex items-center gap-1">
                  <ChevronRight className="h-3 w-3" />
                  {name}
                </span>
              ))}
            </span>
          </div>
        )}

        {/* Content area */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {/* Error state */}
          {loadError && !isGenerating && (
            <div className="rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-400">
              {t('loadFailed')}: {loadError}
            </div>
          )}
          {generateError && (
            <div className="mb-4 rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-400">
              {t('errorGenerating')}: {generateError}
            </div>
          )}

          {/* Loading skeleton */}
          {isLoading && !isGenerating && (
            <div className="space-y-3 animate-pulse">
              <div className="h-6 w-2/3 rounded bg-white/10" />
              <div className="h-4 w-full rounded bg-white/5" />
              <div className="h-4 w-5/6 rounded bg-white/5" />
              <div className="h-4 w-4/5 rounded bg-white/5" />
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !isGenerating && !displayedContent && !loadError && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <BookOpen className="h-12 w-12 text-slate-600 mb-4" />
              <p className="text-sm font-medium text-slate-400">{t('noReport')}</p>
              <p className="text-xs text-slate-600 mt-1">{t('noReportDesc')}</p>
            </div>
          )}

          {/* Report content */}
          {displayedContent && (
            <div className="max-w-3xl">
              {/* Report metadata */}
              {currentReport && !isGenerating && (
                <div className="mb-4 flex items-center gap-3 text-xs text-slate-500">
                  <Clock className="h-3.5 w-3.5" />
                  <span>{formatKST(currentReport.generated_at)}</span>
                  <span>·</span>
                  <span>{currentReport.trigger === 'scheduled' ? t('trigger_scheduled') : t('trigger_manual')}</span>
                  {currentReport.duration_sec != null && (
                    <>
                      <span>·</span>
                      <span>{Math.round(currentReport.duration_sec)}s</span>
                    </>
                  )}
                </div>
              )}
              {/* Rendered markdown */}
              <div className="space-y-0.5">
                {renderMarkdown(displayedContent)}
              </div>
              {/* Streaming cursor */}
              {isGenerating && (
                <span className="inline-block h-4 w-0.5 animate-pulse bg-blue-400 ml-1 align-text-bottom" />
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
