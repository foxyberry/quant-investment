'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import {
  Treemap,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import type { Holding } from '@/lib/types';

interface AllocationChartsProps {
  holdings: Holding[];
  formatCurrency: (amount: number, currency?: string) => string;
  onSectorClick?: (sector: string | null) => void;
  onMarketClick?: (market: string | null) => void;
  onTickerClick?: (ticker: string) => void;
  activeSectorFilter?: string | null;
  activeMarketFilter?: string | null;
}

// Color palette for treemap cells (muted, distinct hues)
const TREEMAP_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
  '#14b8a6', '#e11d48', '#0ea5e9', '#a855f7', '#22c55e',
  '#eab308', '#d946ef', '#64748b', '#f43f5e', '#0891b2',
];

// Market donut colors
export const MARKET_COLORS: Record<string, string> = {
  KOSPI: '#3b82f6',
  KOSDAQ: '#10b981',
  US: '#f59e0b',
  ETF: '#8b5cf6',
  unknown: '#94a3b8',
};

// Sector donut colors
export const SECTOR_COLORS: Record<string, string> = {
  Technology: '#3b82f6',
  Financials: '#10b981',
  Consumer: '#f59e0b',
  Healthcare: '#ef4444',
  Energy: '#8b5cf6',
  Industrials: '#06b6d4',
  Materials: '#84cc16',
  'Real Estate': '#ec4899',
  Utilities: '#f97316',
  Communication: '#6366f1',
  Others: '#94a3b8',
};

export function classifyMarket(ticker: string): string {
  if (ticker.endsWith('.KS')) return 'KOSPI';
  if (ticker.endsWith('.KQ')) return 'KOSDAQ';
  // Simple ETF heuristic: common ETF patterns
  const base = ticker.split('.')[0];
  if (/^(SPY|QQQ|IWM|DIA|VOO|VTI|ARKK|XL[A-Z]|KODEX|TIGER|KBSTAR|KOSEF)/i.test(base)) return 'ETF';
  return 'US';
}

// Explicit mapping for pykrx Korean sector names → normalized category
// pykrx returns names like "전기전자", "음식료품" (no middle dots)
const KR_SECTOR_MAP: Record<string, string> = {
  // Technology
  '전기전자': 'Technology',
  '전기·전자': 'Technology',
  'IT 서비스': 'Technology',
  // Materials
  '화학': 'Materials',
  '철강금속': 'Materials',
  '금속': 'Materials',
  '비금속': 'Materials',
  '종이·목재': 'Materials',
  // Consumer
  '음식료품': 'Consumer',
  '음식료·담배': 'Consumer',
  '섬유의복': 'Consumer',
  '섬유·의류': 'Consumer',
  '유통업': 'Consumer',
  '유통': 'Consumer',
  '오락·문화': 'Consumer',
  '일반서비스': 'Consumer',
  '서비스업': 'Consumer',
  // Industrials
  '건설업': 'Industrials',
  '건설': 'Industrials',
  '기계': 'Industrials',
  '기계·장비': 'Industrials',
  '운수창고업': 'Industrials',
  '운송·창고': 'Industrials',
  '운수장비': 'Industrials',
  '운송장비·부품': 'Industrials',
  '기타제조업': 'Industrials',
  '기타제조': 'Industrials',
  // Healthcare
  '의약품': 'Healthcare',
  '제약': 'Healthcare',
  '의료·정밀기기': 'Healthcare',
  // Financials
  '은행': 'Financials',
  '보험': 'Financials',
  '증권': 'Financials',
  '기타금융': 'Financials',
  '금융': 'Financials',
  // Utilities
  '전기가스업': 'Utilities',
  '전기·가스': 'Utilities',
  '전기·가스·수도': 'Utilities',
  // Communication
  '통신업': 'Communication',
  '통신': 'Communication',
  '출판·매체복제': 'Communication',
  // Real Estate
  '부동산': 'Real Estate',
  // Others
  '농업 임업 및 어업': 'Others',
};

export function normalizeSector(sector: string | null | undefined): string {
  if (!sector) return 'Others';

  // Check exact Korean sector name first (pykrx)
  const mapped = KR_SECTOR_MAP[sector];
  if (mapped) return mapped;

  // Fallback: fuzzy match for yfinance English sectors
  const s = sector.toLowerCase();
  if (s.includes('technol') || s.includes('information')) return 'Technology';
  if (s.includes('financ')) return 'Financials';
  if (s.includes('consumer')) return 'Consumer';
  if (s.includes('health')) return 'Healthcare';
  if (s.includes('energy')) return 'Energy';
  if (s.includes('industrial')) return 'Industrials';
  if (s.includes('material') || s.includes('basic')) return 'Materials';
  if (s.includes('real estate')) return 'Real Estate';
  if (s.includes('utilit')) return 'Utilities';
  if (s.includes('communic')) return 'Communication';
  return 'Others';
}

// Sector key map for i18n
const SECTOR_I18N_KEY: Record<string, string> = {
  Technology: 'technology',
  Financials: 'financials',
  Consumer: 'consumer',
  Healthcare: 'healthcare',
  Energy: 'energy',
  Industrials: 'industrials',
  Materials: 'materials',
  'Real Estate': 'realEstate',
  Utilities: 'utilities',
  Communication: 'communication',
  Others: 'others',
};

const MARKET_I18N_KEY: Record<string, string> = {
  KOSPI: 'kospi',
  KOSDAQ: 'kosdaq',
  US: 'us',
  ETF: 'etf',
  unknown: 'unknown',
};

interface TreemapContentProps {
  x: number;
  y: number;
  width: number;
  height: number;
  name: string;
  pct: number;
  fill: string;
}

function TreemapContent({ x, y, width, height, name, pct, fill }: TreemapContentProps) {
  if (width < 40 || height < 30) return null;
  const fontSize = Math.min(width / 8, height / 3, 14);
  const showPct = width > 55 && height > 40;

  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx={4} fill={fill} stroke="var(--background-secondary)" strokeWidth={2} />
      <text
        x={x + width / 2}
        y={y + height / 2 - (showPct ? 6 : 0)}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#fff"
        fontSize={fontSize}
        fontWeight={600}
      >
        {name}
      </text>
      {showPct && (
        <text
          x={x + width / 2}
          y={y + height / 2 + fontSize}
          textAnchor="middle"
          dominantBaseline="central"
          fill="rgba(255,255,255,0.8)"
          fontSize={fontSize * 0.8}
        >
          {pct.toFixed(1)}%
        </text>
      )}
    </g>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function renderDonutLabel(props: any) {
  const { cx, cy, midAngle, innerRadius, outerRadius, percent, name } = props;
  if (!percent || percent < 0.05) return null;
  const RADIAN = Math.PI / 180;
  const radius = (innerRadius ?? 0) + ((outerRadius ?? 0) - (innerRadius ?? 0)) * 0.5;
  const x = (cx ?? 0) + radius * Math.cos(-(midAngle ?? 0) * RADIAN);
  const y = (cy ?? 0) + radius * Math.sin(-(midAngle ?? 0) * RADIAN);

  return (
    <text x={x} y={y} fill="#fff" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {(name ?? '').length > 5 ? `${(percent * 100).toFixed(0)}%` : `${name}`}
    </text>
  );
}

export default function AllocationCharts({ holdings, formatCurrency, onSectorClick, onMarketClick, onTickerClick, activeSectorFilter, activeMarketFilter }: AllocationChartsProps) {
  const t = useTranslations('allocation');

  const { treemapData, marketData, sectorData, totalInvested } = useMemo(() => {
    const holdingsWithValue = holdings.filter(
      (h) => h.market_value != null && h.market_value > 0
    );

    if (holdingsWithValue.length === 0) {
      return { treemapData: [], marketData: [], sectorData: [], totalInvested: 0 };
    }

    const total = holdingsWithValue.reduce((sum, h) => sum + (h.market_value ?? 0), 0);

    // Treemap: per-stock allocation
    const treeItems = holdingsWithValue
      .map((h, i) => ({
        name: h.name || h.ticker,
        ticker: h.ticker,
        value: h.market_value ?? 0,
        pct: ((h.market_value ?? 0) / total) * 100,
        fill: TREEMAP_COLORS[i % TREEMAP_COLORS.length],
      }))
      .sort((a, b) => b.value - a.value);

    // Market donut: group by market
    const marketGroups = new Map<string, number>();
    for (const h of holdingsWithValue) {
      const market = classifyMarket(h.ticker);
      marketGroups.set(market, (marketGroups.get(market) ?? 0) + (h.market_value ?? 0));
    }
    const mktData = Array.from(marketGroups.entries())
      .map(([name, value]) => ({
        name,
        displayName: t(MARKET_I18N_KEY[name] ?? 'unknown'),
        value,
        pct: (value / total) * 100,
        color: MARKET_COLORS[name] ?? '#94a3b8',
      }))
      .sort((a, b) => b.value - a.value);

    // Sector donut: group by sector
    const sectorGroups = new Map<string, number>();
    for (const h of holdingsWithValue) {
      const sector = normalizeSector(h.sector);
      sectorGroups.set(sector, (sectorGroups.get(sector) ?? 0) + (h.market_value ?? 0));
    }
    const secData = Array.from(sectorGroups.entries())
      .map(([name, value]) => ({
        name,
        displayName: t(SECTOR_I18N_KEY[name] ?? 'others'),
        value,
        pct: (value / total) * 100,
        color: SECTOR_COLORS[name] ?? '#94a3b8',
      }))
      .sort((a, b) => b.value - a.value);

    return {
      treemapData: treeItems,
      marketData: mktData,
      sectorData: secData,
      totalInvested: total,
    };
  }, [holdings, t]);

  if (treemapData.length === 0) {
    return null;
  }

  // Determine primary currency from first holding
  const primaryCurrency = holdings[0]?.currency ?? 'KRW';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Treemap: Stock Allocation */}
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-sm lg:row-span-2">
        <div className="border-b border-[var(--border)] px-6 py-4">
          <h3 className="text-lg font-semibold text-[var(--foreground)]">{t('stockAllocation')}</h3>
          <p className="text-sm text-[var(--foreground-muted)] mt-1">
            {treemapData.length} {t('totalHoldings')} &middot; {formatCurrency(totalInvested, primaryCurrency)}
          </p>
        </div>
        <div className="p-4">
          <ResponsiveContainer width="100%" height={360}>
            <Treemap
              data={treemapData}
              dataKey="value"
              stroke="none"
              content={<TreemapContent x={0} y={0} width={0} height={0} name="" pct={0} fill="" />}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onClick={onTickerClick ? (node: any) => {
                if (node?.ticker) onTickerClick(node.ticker);
              } : undefined}
              style={onTickerClick ? { cursor: 'pointer' } : undefined}
            >
              <Tooltip
                content={({ payload }) => {
                  if (!payload || payload.length === 0) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 shadow-lg text-sm">
                      <div className="font-semibold text-[var(--foreground)]">{d.name}</div>
                      <div className="text-[var(--foreground-muted)]">{d.ticker}</div>
                      <div className="mt-1 text-[var(--foreground)]">{d.pct.toFixed(1)}%</div>
                    </div>
                  );
                }}
              />
            </Treemap>
          </ResponsiveContainer>
          {/* Legend: top 5 stocks */}
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--foreground-muted)]">
            {treemapData.slice(0, 5).map((item) => (
              <span key={item.ticker} className="flex items-center gap-1">
                <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: item.fill }} />
                {item.name} {item.pct.toFixed(1)}%
              </span>
            ))}
            {treemapData.length > 5 && (
              <span className="text-[var(--foreground-muted)]">+{treemapData.length - 5} {t('others').toLowerCase()}</span>
            )}
          </div>
        </div>
      </div>

      {/* Market Donut */}
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-sm">
        <div className="border-b border-[var(--border)] px-6 py-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-[var(--foreground)]">{t('marketAllocation')}</h3>
          {activeMarketFilter && (
            <button
              type="button"
              onClick={() => onMarketClick?.(null)}
              className="text-xs text-[var(--color-primary)] hover:underline"
            >
              {t('clearFilter')}
            </button>
          )}
        </div>
        <div className="p-4 flex items-center gap-4">
          <div className="w-1/2 flex-shrink-0">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={marketData}
                  dataKey="value"
                  nameKey="displayName"
                  cx="50%"
                  cy="50%"
                  innerRadius="50%"
                  outerRadius="90%"
                  strokeWidth={2}
                  stroke="var(--background-secondary)"
                  label={renderDonutLabel}
                  labelLine={false}
                  onClick={onMarketClick ? (_: unknown, index: number) => {
                    const clicked = marketData[index]?.name;
                    if (clicked) onMarketClick(activeMarketFilter === clicked ? null : clicked);
                  } : undefined}
                  style={onMarketClick ? { cursor: 'pointer' } : undefined}
                >
                  {marketData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={entry.color}
                      opacity={activeMarketFilter && activeMarketFilter !== entry.name ? 0.3 : 1}
                    />
                  ))}
                </Pie>
                <Tooltip
                  content={({ payload }) => {
                    if (!payload || payload.length === 0) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 shadow-lg text-sm">
                        <div className="font-semibold text-[var(--foreground)]">{d.displayName}</div>
                        <div className="text-[var(--foreground)]">{d.pct.toFixed(1)}%</div>
                      </div>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-col gap-2 text-sm">
            {marketData.map((item) => (
              <button
                key={item.name}
                type="button"
                onClick={() => onMarketClick?.(activeMarketFilter === item.name ? null : item.name)}
                className={`flex items-center gap-2 rounded-md px-2 py-1 transition-colors text-left ${
                  activeMarketFilter === item.name
                    ? 'bg-[var(--color-primary)]/10 ring-1 ring-[var(--color-primary)]'
                    : 'hover:bg-[var(--background)]/50'
                } ${activeMarketFilter && activeMarketFilter !== item.name ? 'opacity-40' : ''}`}
              >
                <span className="inline-block h-3 w-3 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
                <span className="text-[var(--foreground)]">{item.displayName}</span>
                <span className="text-[var(--foreground-muted)] ml-auto">{item.pct.toFixed(1)}%</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Sector Donut */}
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-sm">
        <div className="border-b border-[var(--border)] px-6 py-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-[var(--foreground)]">{t('sectorAllocation')}</h3>
          {activeSectorFilter && (
            <button
              type="button"
              onClick={() => onSectorClick?.(null)}
              className="text-xs text-[var(--color-primary)] hover:underline"
            >
              {t('clearFilter')}
            </button>
          )}
        </div>
        <div className="p-4 flex items-center gap-4">
          <div className="w-1/2 flex-shrink-0">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={sectorData}
                  dataKey="value"
                  nameKey="displayName"
                  cx="50%"
                  cy="50%"
                  innerRadius="50%"
                  outerRadius="90%"
                  strokeWidth={2}
                  stroke="var(--background-secondary)"
                  label={renderDonutLabel}
                  labelLine={false}
                  onClick={onSectorClick ? (_: unknown, index: number) => {
                    const clicked = sectorData[index]?.name;
                    if (clicked) onSectorClick(activeSectorFilter === clicked ? null : clicked);
                  } : undefined}
                  style={onSectorClick ? { cursor: 'pointer' } : undefined}
                >
                  {sectorData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={entry.color}
                      opacity={activeSectorFilter && activeSectorFilter !== entry.name ? 0.3 : 1}
                    />
                  ))}
                </Pie>
                <Tooltip
                  content={({ payload }) => {
                    if (!payload || payload.length === 0) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 shadow-lg text-sm">
                        <div className="font-semibold text-[var(--foreground)]">{d.displayName}</div>
                        <div className="text-[var(--foreground)]">{d.pct.toFixed(1)}%</div>
                      </div>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-col gap-2 text-sm">
            {sectorData.map((item) => (
              <button
                key={item.name}
                type="button"
                onClick={() => onSectorClick?.(activeSectorFilter === item.name ? null : item.name)}
                className={`flex items-center gap-2 rounded-md px-2 py-1 transition-colors text-left ${
                  activeSectorFilter === item.name
                    ? 'bg-[var(--color-primary)]/10 ring-1 ring-[var(--color-primary)]'
                    : 'hover:bg-[var(--background)]/50'
                } ${activeSectorFilter && activeSectorFilter !== item.name ? 'opacity-40' : ''}`}
              >
                <span className="inline-block h-3 w-3 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
                <span className="text-[var(--foreground)]">{item.displayName}</span>
                <span className="text-[var(--foreground-muted)] ml-auto">{item.pct.toFixed(1)}%</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
