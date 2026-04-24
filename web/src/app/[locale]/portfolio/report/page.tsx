'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { RefreshCw, Loader2, Clock, BookOpen, Send } from 'lucide-react';
import {
  listReports,
  getLatestReport,
  generateReportBackground,
  getReportStatus,
  sendReportToSlack,
} from '@/lib/api';
import type { ReportSummary, ReportDetail } from '@/lib/types';

// ── Markdown renderer ─────────────────────────────────────────────────────────

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
        <ul key={`ul-${nodeKey++}`} className="my-1.5 ml-4 list-disc space-y-0.5">
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
        return <strong key={i} className="font-semibold text-white">{part.slice(2, -2)}</strong>;
      if (part.startsWith('*') && part.endsWith('*'))
        return <em key={i} className="italic text-slate-300">{part.slice(1, -1)}</em>;
      if (part.startsWith('`') && part.endsWith('`'))
        return <code key={i} className="rounded bg-white/10 px-1 py-0.5 font-mono text-xs text-blue-300">{part.slice(1, -1)}</code>;
      return part;
    });
  };

  for (const line of lines) {
    if (line.startsWith('## ')) {
      flushList(); flushTable();
      result.push(
        <h2 key={`h2-${nodeKey++}`} className="mt-6 mb-2 text-base font-bold text-white border-b border-white/10 pb-1.5">
          {inlineMarkdown(line.slice(3))}
        </h2>
      );
      continue;
    }
    if (line.startsWith('### ')) {
      flushList(); flushTable();
      result.push(
        <h3 key={`h3-${nodeKey++}`} className="mt-4 mb-1.5 text-sm font-semibold text-slate-200">
          {inlineMarkdown(line.slice(4))}
        </h3>
      );
      continue;
    }
    if (line.startsWith('#### ')) {
      flushList(); flushTable();
      result.push(
        <h4 key={`h4-${nodeKey++}`} className="mt-3 mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
          {inlineMarkdown(line.slice(5))}
        </h4>
      );
      continue;
    }
    if (/^---+$/.test(line.trim())) {
      flushList(); flushTable();
      result.push(<hr key={`hr-${nodeKey++}`} className="my-4 border-white/10" />);
      continue;
    }
    if (line.startsWith('> ')) {
      flushList(); flushTable();
      result.push(
        <blockquote key={`bq-${nodeKey++}`} className="my-1.5 border-l-2 border-blue-500 pl-3 text-xs italic text-slate-400">
          {inlineMarkdown(line.slice(2))}
        </blockquote>
      );
      continue;
    }
    if (line.startsWith('|') && line.endsWith('|')) {
      if (/^[\s|:-]+$/.test(line)) continue; // separator
      flushList();
      const cells = line.slice(1, -1).split('|');
      if (tableHeader === null) {
        tableHeader = cells;
      } else {
        tableRows.push(cells);
      }
      continue;
    }
    if (/^[-*]\s/.test(line)) {
      flushTable();
      listItems.push(
        <li key={`li-${nodeKey++}`} className="text-xs text-slate-300">
          {inlineMarkdown(line.replace(/^[-*]\s/, ''))}
        </li>
      );
      continue;
    }
    if (line.trim() === '') {
      flushList(); flushTable();
      result.push(<div key={`sp-${nodeKey++}`} className="h-2" />);
      continue;
    }
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
    const d = new Date(isoString.endsWith('Z') ? isoString : isoString + 'Z');
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
    const d = new Date(isoString.endsWith('Z') ? isoString : isoString + 'Z');
    const now = new Date();
    // Compare in KST
    const kstOffset = 9 * 60 * 60 * 1000;
    const dKST = new Date(d.getTime() + kstOffset);
    const nowKST = new Date(now.getTime() + kstOffset);
    return dKST.toDateString() === nowKST.toDateString();
  } catch {
    return false;
  }
}

const POLL_INTERVAL_MS = 5000;

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DailyReportPage() {
  const t = useTranslations('dailyReport');

  const [currentReport, setCurrentReport] = useState<ReportDetail | null>(null);
  const [history, setHistory] = useState<ReportSummary[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [slackStatus, setSlackStatus] = useState<'idle' | 'sending' | 'sent' | 'failed'>('idle');

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const latestIdRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const refreshData = useCallback(async () => {
    try {
      const [latest, summaries] = await Promise.all([
        getLatestReport(),
        listReports(20),
      ]);
      setCurrentReport(latest);
      setHistory(summaries);
      return latest;
    } catch (e: unknown) {
      setLoadError(e instanceof Error ? e.message : String(e));
      return null;
    }
  }, []);

  const startPolling = useCallback((sinceId: number | null) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        // Check for a newer report first
        const latest = await getLatestReport();
        if (latest && latest.id !== sinceId) {
          stopPolling();
          setIsGenerating(false);
          await refreshData();
          return;
        }
        // Also check status endpoint (may not exist on older backend)
        try {
          const status = await getReportStatus();
          if (!status.is_generating) {
            stopPolling();
            setIsGenerating(false);
            await refreshData();
          }
        } catch { /* endpoint unavailable — keep polling by report id */ }
      } catch {
        // network hiccup — keep polling
      }
    }, POLL_INTERVAL_MS);
  }, [stopPolling, refreshData]);

  // On mount: load data + check if generation is already in progress
  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const [latest, summaries] = await Promise.all([
          getLatestReport(),
          listReports(20),
        ]);
        if (cancelled) return;
        setCurrentReport(latest);
        setHistory(summaries);
        latestIdRef.current = latest?.id ?? null;

        // Check background status separately — endpoint may not exist on older backends
        let isGen = false;
        try {
          const status = await getReportStatus();
          isGen = status.is_generating;
        } catch { /* endpoint unavailable — ignore */ }

        if (isGen) {
          setIsGenerating(true);
          startPolling(latestIdRef.current);
        } else if (!latest) {
          // No report at all — auto-generate
          void triggerGenerate(null);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : String(e);
          setLoadError(msg.startsWith('[object') ? '서버에 연결할 수 없습니다.' : msg);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    void init();
    return () => {
      cancelled = true;
      stopPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const triggerGenerate = useCallback(async (currentId: number | null) => {
    if (isGenerating) return;
    setIsGenerating(true);
    setGenerateError(null);
    setSlackStatus('idle');
    latestIdRef.current = currentId;

    try {
      await generateReportBackground();
      startPolling(currentId);
    } catch (e: unknown) {
      setIsGenerating(false);
      setGenerateError(e instanceof Error ? e.message : String(e));
    }
  }, [isGenerating, startPolling]);

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
      const { getReport } = await import('@/lib/api');
      const detail = await getReport(id);
      if (detail) setCurrentReport(detail);
    } catch { /* ignore */ }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#0d1117]">
      {/* ── History sidebar ── */}
      <aside className="hidden w-64 flex-shrink-0 border-r border-white/10 bg-[#0a0f16] lg:flex lg:flex-col">
        <div className="border-b border-white/10 px-4 py-4">
          <h2 className="text-sm font-semibold text-slate-300">{t('history')}</h2>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          {isGenerating && (
            <div className="flex items-center gap-2 px-4 py-3 text-xs text-blue-400">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>{t('generating')}</span>
            </div>
          )}
          {history.length === 0 && !isLoading && !isGenerating && (
            <p className="px-4 py-3 text-xs text-slate-500">생성된 리포트가 없습니다</p>
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
                <span className="truncate text-[11px] font-medium text-slate-200">
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
      <main className="flex flex-1 flex-col overflow-hidden bg-[#0d1117]">
        {/* Header */}
        <header className="flex flex-shrink-0 items-center justify-between border-b border-white/10 bg-[#0a0f16] px-6 py-4">
          <div className="flex items-center gap-3">
            <BookOpen className="h-5 w-5 text-blue-400" />
            <div>
              <h1 className="text-base font-semibold text-white">{t('title')}</h1>
              <p className="text-xs text-slate-500">{t('subtitle')}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {currentReport && !isGenerating && (
              <button
                type="button"
                onClick={() => void handleSlack()}
                disabled={slackStatus === 'sending' || slackStatus === 'sent'}
                className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:bg-white/10 disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5" />
                {slackStatus === 'sending' ? '...' : slackStatus === 'sent' ? t('sent') : slackStatus === 'failed' ? t('sendFailed') : t('sendToSlack')}
              </button>
            )}
            <button
              type="button"
              onClick={() => void triggerGenerate(currentReport?.id ?? null)}
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

        {/* Content area */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {/* Errors */}
          {loadError && (
            <div className="mb-4 rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-400">
              {t('loadFailed')}: {loadError}
            </div>
          )}
          {generateError && (
            <div className="mb-4 rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-400">
              {t('errorGenerating')}: {generateError}
            </div>
          )}

          {/* Loading skeleton */}
          {isLoading && (
            <div className="space-y-3 animate-pulse">
              <div className="h-6 w-2/3 rounded bg-white/10" />
              <div className="h-4 w-full rounded bg-white/5" />
              <div className="h-4 w-5/6 rounded bg-white/5" />
              <div className="h-4 w-4/5 rounded bg-white/5" />
            </div>
          )}

          {/* Generating indicator */}
          {!isLoading && isGenerating && !currentReport && (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <Loader2 className="h-10 w-10 animate-spin text-blue-400" />
              <p className="text-sm text-slate-400">{t('generating')}</p>
              <p className="text-xs text-slate-600">다른 페이지를 이용하셔도 백그라운드에서 생성됩니다.</p>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !isGenerating && !currentReport && !loadError && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <BookOpen className="h-12 w-12 text-slate-600 mb-4" />
              <p className="text-sm font-medium text-slate-400">오늘 리포트가 없어요</p>
              <p className="text-xs text-slate-600 mt-1 mb-6">위의 "새 리포트 생성" 버튼을 눌러 AI 분석을 시작해보세요.</p>
            </div>
          )}

          {/* Report content */}
          {currentReport && (
            <div className="max-w-3xl">
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
                {isGenerating && (
                  <>
                    <span>·</span>
                    <span className="flex items-center gap-1 text-blue-400">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      새 리포트 생성 중
                    </span>
                  </>
                )}
              </div>
              <div className="space-y-0.5">
                {renderMarkdown(currentReport.content)}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
