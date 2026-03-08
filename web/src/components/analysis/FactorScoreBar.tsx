'use client';

import {
  DollarSign,
  Award,
  TrendingUp,
  MessageSquare,
  ShieldAlert,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { TechnicalIndicators, TickerAnalysis } from '@/lib/types';

type Signal = 'bullish' | 'neutral' | 'bearish';

interface FactorScore {
  name: string;
  signal: Signal;
  preview: string;
  icon: React.ReactNode;
}

interface FactorScoreBarProps {
  tickerData: TickerAnalysis;
  className?: string;
}

function computeValuationSignal(fundamental: TickerAnalysis['fundamental']): { signal: Signal; preview: string } {
  if (!fundamental) return { signal: 'neutral', preview: 'N/A' };
  let score = 0;
  let count = 0;
  const pe = fundamental.pe_ratio;
  if (pe != null) {
    count++;
    if (pe < 15) score += 1;
    else if (pe > 30) score -= 1;
  }
  const fpe = fundamental.forward_pe;
  if (fpe != null) {
    count++;
    if (fpe < 15) score += 1;
    else if (fpe > 30) score -= 1;
  }
  const pb = fundamental.pb_ratio;
  if (pb != null) {
    count++;
    if (pb < 3) score += 1;
    else if (pb > 10) score -= 1;
  }
  const ps = fundamental.ps_ratio;
  if (ps != null) {
    count++;
    if (ps < 5) score += 1;
    else if (ps > 15) score -= 1;
  }
  const peg = fundamental.peg_ratio;
  if (peg != null) {
    count++;
    if (peg < 1) score += 1;
    else if (peg > 2) score -= 1;
  }
  if (count === 0) return { signal: 'neutral', preview: 'N/A' };
  const avg = score / count;
  const mainMetric = pe != null ? `P/E ${pe.toFixed(1)}` : 'N/A';
  if (avg > 0.2) return { signal: 'bullish', preview: mainMetric };
  if (avg < -0.2) return { signal: 'bearish', preview: mainMetric };
  return { signal: 'neutral', preview: mainMetric };
}

function computeQualitySignal(fundamental: TickerAnalysis['fundamental']): { signal: Signal; preview: string } {
  if (!fundamental) return { signal: 'neutral', preview: 'N/A' };
  let score = 0;
  let count = 0;
  const roe = fundamental.roe;
  if (roe != null) {
    count++;
    if (roe > 15) score += 1;
    else if (roe < 5) score -= 1;
  }
  const roa = fundamental.roa;
  if (roa != null) {
    count++;
    if (roa > 10) score += 1;
    else if (roa < 2) score -= 1;
  }
  const margin = fundamental.profit_margin;
  if (margin != null) {
    count++;
    if (margin > 20) score += 1;
    else if (margin < 5) score -= 1;
  }
  const de = fundamental.debt_to_equity;
  if (de != null) {
    count++;
    if (de < 0.5) score += 1;
    else if (de > 2) score -= 1;
  }
  const cr = fundamental.current_ratio;
  if (cr != null) {
    count++;
    if (cr > 1.5) score += 1;
    else if (cr < 1) score -= 1;
  }
  if (count === 0) return { signal: 'neutral', preview: 'N/A' };
  const avg = score / count;
  const mainMetric = roe != null ? `ROE ${roe.toFixed(1)}%` : 'N/A';
  if (avg > 0.2) return { signal: 'bullish', preview: mainMetric };
  if (avg < -0.2) return { signal: 'bearish', preview: mainMetric };
  return { signal: 'neutral', preview: mainMetric };
}

function computeMomentumSignal(technical: TechnicalIndicators): { signal: Signal; preview: string } {
  let score = 0;
  let count = 0;
  if (technical.rsi) {
    count++;
    if (technical.rsi.signal === 'oversold') score += 1;
    else if (technical.rsi.signal === 'overbought') score -= 1;
  }
  if (technical.macd) {
    count++;
    if (technical.macd.trend === 'bullish') score += 1;
    else if (technical.macd.trend === 'bearish') score -= 1;
  }
  if (technical.stochastic) {
    count++;
    const k = technical.stochastic.k;
    if (k < 20) score += 1;
    else if (k > 80) score -= 1;
  }
  if (count === 0) return { signal: 'neutral', preview: 'N/A' };
  const avg = score / count;
  const mainMetric = technical.rsi ? `RSI ${technical.rsi.value.toFixed(0)}` : 'N/A';
  if (avg > 0.2) return { signal: 'bullish', preview: mainMetric };
  if (avg < -0.2) return { signal: 'bearish', preview: mainMetric };
  return { signal: 'neutral', preview: mainMetric };
}

function computeSentimentSignal(
  technical: TechnicalIndicators,
  news?: TickerAnalysis['news'],
): { signal: Signal; preview: string } {
  let score = 0;
  let count = 0;
  if (technical.obv) {
    count++;
    if (technical.obv.trend === 'rising') score += 1;
    else if (technical.obv.trend === 'falling') score -= 1;
  }
  if (news?.sentiment_summary) {
    count++;
    const s = news.sentiment_summary.toLowerCase();
    if (s.includes('positive') || s.includes('bullish')) score += 1;
    else if (s.includes('negative') || s.includes('bearish')) score -= 1;
  }
  if (count === 0) return { signal: 'neutral', preview: 'N/A' };
  const avg = score / count;
  const preview = technical.obv
    ? `OBV ${technical.obv.trend}`
    : 'N/A';
  if (avg > 0.2) return { signal: 'bullish', preview };
  if (avg < -0.2) return { signal: 'bearish', preview };
  return { signal: 'neutral', preview };
}

function computeRiskSignal(
  technical: TechnicalIndicators,
  fundamental?: TickerAnalysis['fundamental'],
  currentPrice?: number,
): { signal: Signal; preview: string } {
  let riskCount = 0;
  let total = 0;
  if (technical.bollingerBands) {
    total++;
    if (technical.bollingerBands.position === 'above') riskCount++;
  }
  if (fundamental?.week52_high != null && fundamental?.week52_low != null && currentPrice) {
    total++;
    const range = fundamental.week52_high - fundamental.week52_low;
    if (range > 0) {
      const pos = (currentPrice - fundamental.week52_low) / range;
      if (pos > 0.9) riskCount++;
    }
  }
  if (technical.volume) {
    total++;
    if (technical.volume.ratio > 2) riskCount++;
  }
  if (total === 0) return { signal: 'neutral', preview: 'N/A' };
  const preview = technical.bollingerBands
    ? `BB ${technical.bollingerBands.position}`
    : 'N/A';
  if (riskCount === 0) return { signal: 'bullish', preview };
  if (riskCount >= 2) return { signal: 'bearish', preview };
  return { signal: 'neutral', preview };
}

const signalColors: Record<Signal, { bg: string; text: string; label: string }> = {
  bullish: { bg: 'bg-green-500/15', text: 'text-green-500', label: 'Bullish' },
  neutral: { bg: 'bg-yellow-500/15', text: 'text-yellow-500', label: 'Neutral' },
  bearish: { bg: 'bg-red-500/15', text: 'text-red-500', label: 'Bearish' },
};

export default function FactorScoreBar({ tickerData, className = '' }: FactorScoreBarProps) {
  const t = useTranslations('factors');

  const valuation = computeValuationSignal(tickerData.fundamental);
  const quality = computeQualitySignal(tickerData.fundamental);
  const momentum = computeMomentumSignal(tickerData.technical);
  const sentiment = computeSentimentSignal(tickerData.technical, tickerData.news);
  const risk = computeRiskSignal(tickerData.technical, tickerData.fundamental, tickerData.current_price);

  const factors: FactorScore[] = [
    { name: t('valuation'), icon: <DollarSign className="h-4 w-4" />, ...valuation },
    { name: t('quality'), icon: <Award className="h-4 w-4" />, ...quality },
    { name: t('momentum'), icon: <TrendingUp className="h-4 w-4" />, ...momentum },
    { name: t('sentiment'), icon: <MessageSquare className="h-4 w-4" />, ...sentiment },
    { name: t('risk'), icon: <ShieldAlert className="h-4 w-4" />, ...risk },
  ];

  return (
    <div className={`grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 ${className}`}>
      {factors.map((factor) => {
        const colors = signalColors[factor.signal];
        return (
          <div
            key={factor.name}
            className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[var(--foreground-muted)]">{factor.icon}</span>
              <span className="text-sm font-medium text-[var(--foreground)]">{factor.name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--foreground-muted)] font-mono">{factor.preview}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${colors.bg} ${colors.text}`}>
                {t(factor.signal)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
