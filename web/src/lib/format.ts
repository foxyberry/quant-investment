/**
 * Locale-aware formatting utilities for currency, numbers, and percentages.
 *
 * UI language and number formatting locale are kept in sync:
 *   'en' → 'en-US', 'ko' → 'ko-KR', 'zh' → 'zh-CN'
 *
 * Currency is determined by the holding's native currency (per-row),
 * NOT by the UI language. A Korean-language UI can still display USD prices.
 */

const LOCALE_MAP: Record<string, string> = {
  en: 'en-US',
  ko: 'ko-KR',
  zh: 'zh-CN',
};

/** Resolve a next-intl locale to an Intl-compatible locale string. */
export function resolveIntlLocale(locale: string): string {
  return LOCALE_MAP[locale] ?? 'en-US';
}

/** Format a number as currency using the holding's native currency and the UI locale. */
export function formatCurrency(
  value: number | null,
  currency: string = 'USD',
  locale: string = 'en',
): string {
  if (value === null) return '-';
  return new Intl.NumberFormat(resolveIntlLocale(locale), {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/** Format a number as a signed percentage string. */
export function formatPercent(value: number | null): string {
  if (value === null) return '-';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/** Format a quantity with locale-aware thousand separators. */
export function formatQuantity(value: number, locale: string = 'en'): string {
  if (Number.isInteger(value)) {
    return value.toLocaleString(resolveIntlLocale(locale));
  }
  return value.toLocaleString(resolveIntlLocale(locale), {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  });
}

/** Supported base currencies for portfolio aggregation. */
export const BASE_CURRENCIES = [
  'USD',
  'KRW',
  'SGD',
  'JPY',
  'EUR',
  'GBP',
  'CNY',
  'HKD',
] as const;

export type BaseCurrency = (typeof BASE_CURRENCIES)[number];

/** Human-readable labels for base currencies. */
export const CURRENCY_LABELS: Record<BaseCurrency, string> = {
  USD: 'US Dollar (USD)',
  KRW: 'Korean Won (KRW)',
  SGD: 'Singapore Dollar (SGD)',
  JPY: 'Japanese Yen (JPY)',
  EUR: 'Euro (EUR)',
  GBP: 'British Pound (GBP)',
  CNY: 'Chinese Yuan (CNY)',
  HKD: 'Hong Kong Dollar (HKD)',
};
