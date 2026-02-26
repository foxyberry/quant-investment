'use client';

import { useEffect, useRef, useState } from 'react';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  ColorType,
} from 'lightweight-charts';
import type { IChartApi, ISeriesApi, CandlestickData, HistogramData, Time, LineWidth } from 'lightweight-charts';
import { useTranslations } from 'next-intl';
import type { OHLCVData } from '@/lib/types';

interface CandleChartProps {
  /** OHLCV data array */
  data: OHLCVData[];
  /** Chart height in pixels */
  height?: number;
  /** Show volume histogram */
  showVolume?: boolean;
  /** Show moving average lines (SMA 5, 20, 60, 120) */
  showMA?: boolean;
  /** Additional CSS class */
  className?: string;
}

/** MA line display configurations */
const MA_CONFIGS = [
  { period: 5, color: '#f59e0b', lineWidth: 1 as LineWidth },
  { period: 20, color: '#3b82f6', lineWidth: 1 as LineWidth },
  { period: 60, color: '#8b5cf6', lineWidth: 1 as LineWidth },
  { period: 120, color: '#ef4444', lineWidth: 1 as LineWidth },
] as const;

/** Calculate Simple Moving Average from OHLCV data */
function calculateSMA(data: OHLCVData[], period: number): { time: string; value: number }[] {
  const result: { time: string; value: number }[] = [];
  for (let i = period - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    result.push({ time: data[i].time, value: sum / period });
  }
  return result;
}

/**
 * Candlestick chart component using TradingView's lightweight-charts v5
 */
export default function CandleChart({
  data,
  height = 400,
  showVolume = true,
  showMA = true,
  className = '',
}: CandleChartProps) {
  const t = useTranslations('stockDetail');
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const maSeriesRefs = useRef<(ISeriesApi<'Line'> | null)[]>([]);
  const [isDarkMode, setIsDarkMode] = useState(false);

  // Detect dark mode
  useEffect(() => {
    const checkDarkMode = () => {
      const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDarkMode(dark);
    };

    checkDarkMode();
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', checkDarkMode);

    return () => mediaQuery.removeEventListener('change', checkDarkMode);
  }, []);

  // Initialize chart (dark mode is handled separately via applyOptions)
  useEffect(() => {
    if (!containerRef.current) return;

    const initialWidth = containerRef.current.clientWidth || containerRef.current.offsetWidth || 300;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#ffffff' },
        textColor: '#64748b',
      },
      grid: {
        vertLines: { color: '#e2e8f0' },
        horzLines: { color: '#e2e8f0' },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: '#e2e8f0' },
      timeScale: {
        borderColor: '#e2e8f0',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { vertTouchDrag: false },
      width: initialWidth,
      height: height,
    });

    chartRef.current = chart;

    // Create candlestick series using v5 API
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    candleSeriesRef.current = candleSeries;

    // Create volume series if enabled
    if (showVolume) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: '#60a5fa',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '',
      });

      volumeSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });

      volumeSeriesRef.current = volumeSeries;
    }

    // Create moving average line series if enabled
    if (showMA) {
      maSeriesRefs.current = MA_CONFIGS.map((cfg) => {
        const series = chart.addSeries(LineSeries, {
          color: cfg.color,
          lineWidth: cfg.lineWidth,
          crosshairMarkerVisible: false,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        return series;
      });
    } else {
      maSeriesRefs.current = [];
    }

    // Handle resize with ResizeObserver (works in popups where initial width may be 0)
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const newWidth = entry.contentRect.width;
        if (newWidth > 0 && chartRef.current) {
          chartRef.current.applyOptions({ width: newWidth });
        }
      }
    });

    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      maSeriesRefs.current = [];
    };
  }, [height, showVolume, showMA]);

  // Update data
  useEffect(() => {
    if (!candleSeriesRef.current || data.length === 0) return;

    // Convert OHLCV data to chart format
    const candleData: CandlestickData<Time>[] = data.map((item) => ({
      time: item.time as Time,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    }));

    candleSeriesRef.current.setData(candleData);

    // Update volume data if enabled
    if (showVolume && volumeSeriesRef.current) {
      const volumeData: HistogramData<Time>[] = data.map((item) => ({
        time: item.time as Time,
        value: item.volume || 0,
        color: item.close >= item.open ? '#22c55e80' : '#ef444480',
      }));

      volumeSeriesRef.current.setData(volumeData);
    }

    // Update moving average data
    if (showMA && maSeriesRefs.current.length > 0) {
      MA_CONFIGS.forEach((cfg, idx) => {
        const series = maSeriesRefs.current[idx];
        if (series) {
          const smaData = calculateSMA(data, cfg.period);
          series.setData(smaData.map((d) => ({ time: d.time as Time, value: d.value })));
        }
      });
    }

    // Fit content
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [data, showVolume, showMA]);

  // Update chart colors on theme change
  useEffect(() => {
    if (!chartRef.current) return;

    chartRef.current.applyOptions({
      layout: {
        background: {
          type: ColorType.Solid,
          color: isDarkMode ? '#1e293b' : '#ffffff',
        },
        textColor: isDarkMode ? '#94a3b8' : '#64748b',
      },
      grid: {
        vertLines: {
          color: isDarkMode ? '#334155' : '#e2e8f0',
        },
        horzLines: {
          color: isDarkMode ? '#334155' : '#e2e8f0',
        },
      },
      rightPriceScale: {
        borderColor: isDarkMode ? '#334155' : '#e2e8f0',
      },
      timeScale: {
        borderColor: isDarkMode ? '#334155' : '#e2e8f0',
      },
    });
  }, [isDarkMode]);

  if (data.length === 0) {
    return (
      <div
        className={`flex items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] ${className}`}
        style={{ height }}
      >
        <p className="text-[var(--foreground-muted)]">{t('noChartData')}</p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`rounded-lg border border-[var(--border)] overflow-hidden ${className}`}
      style={{ height }}
    />
  );
}
