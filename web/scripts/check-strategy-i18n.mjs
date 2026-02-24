import fs from 'node:fs';
import path from 'node:path';

const messagePaths = {
  en: path.join(process.cwd(), 'messages', 'en.json'),
  ko: path.join(process.cwd(), 'messages', 'ko.json'),
  zh: path.join(process.cwd(), 'messages', 'zh.json'),
};

function loadStrategyMessages(locale) {
  const raw = fs.readFileSync(messagePaths[locale], 'utf8');
  const json = JSON.parse(raw);
  return json.strategy ?? {};
}

function flattenKeys(obj, prefix = '') {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) {
    return [];
  }

  const keys = [];
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    keys.push(fullKey);
    keys.push(...flattenKeys(obj[key], fullKey));
  }
  return keys;
}

function validate() {
  const locales = ['en', 'ko', 'zh'];
  const strategyByLocale = Object.fromEntries(locales.map((loc) => [loc, loadStrategyMessages(loc)]));

  const baseline = new Set(flattenKeys(strategyByLocale.en));
  const issues = [];

  for (const locale of ['ko', 'zh']) {
    const currentKeys = new Set(flattenKeys(strategyByLocale[locale]));

    for (const key of baseline) {
      if (!currentKeys.has(key)) {
        issues.push(`[${locale}] missing key: strategy.${key}`);
      }
    }

    for (const key of currentKeys) {
      if (!baseline.has(key)) {
        issues.push(`[${locale}] extra key: strategy.${key}`);
      }
    }
  }

  const requiredKey = 'loadingConditions';
  for (const locale of locales) {
    const value = strategyByLocale[locale][requiredKey];
    if (typeof value !== 'string' || value.trim().length === 0) {
      issues.push(`[${locale}] missing/empty key: strategy.${requiredKey}`);
    }
  }

  if (issues.length > 0) {
    console.error('Strategy i18n keyset check failed.');
    for (const issue of issues) {
      console.error(`- ${issue}`);
    }
    process.exit(1);
  }

  console.log(`Strategy i18n keyset OK. locales=${locales.join(',')}, keys=${baseline.size}`);
}

validate();
