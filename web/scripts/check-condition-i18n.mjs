import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(process.cwd(), '..');
const conditionsDir = path.join(repoRoot, 'screener', 'conditions');
const messagePaths = {
  en: path.join(process.cwd(), 'messages', 'en.json'),
  ko: path.join(process.cwd(), 'messages', 'ko.json'),
  zh: path.join(process.cwd(), 'messages', 'zh.json'),
};

const registerPattern = /@register_condition\((.*?)\)\s*class\s/gs;
const keyPattern = /key\s*=\s*"([a-z0-9_]+)"/;
const paramPattern = /"name"\s*:\s*"([a-z0-9_]+)"/g;
const metaKeys = new Set(['recommended', 'categories']);

function parseRegistry() {
  const files = fs.readdirSync(conditionsDir).filter((name) => name.endsWith('.py'));
  const registry = new Map();

  for (const file of files) {
    const fullPath = path.join(conditionsDir, file);
    const text = fs.readFileSync(fullPath, 'utf8');

    for (const match of text.matchAll(registerPattern)) {
      const block = match[1];
      const keyMatch = block.match(keyPattern);
      if (!keyMatch) continue;

      const key = keyMatch[1];
      const params = new Set();
      for (const pm of block.matchAll(paramPattern)) {
        params.add(pm[1]);
      }
      registry.set(key, Array.from(params).sort());
    }
  }

  return registry;
}

function loadConditions(locale) {
  const raw = fs.readFileSync(messagePaths[locale], 'utf8');
  const json = JSON.parse(raw);
  return json.conditions ?? {};
}

function pushIssue(issues, locale, key, field, detail = '') {
  issues.push(`[${locale}] ${key}: missing ${field}${detail ? ` (${detail})` : ''}`);
}

function validate() {
  const registry = parseRegistry();
  const locales = ['en', 'ko', 'zh'];
  const localized = Object.fromEntries(locales.map((loc) => [loc, loadConditions(loc)]));
  const issues = [];

  for (const [key, params] of registry.entries()) {
    for (const locale of locales) {
      const entry = localized[locale][key];
      if (!entry || typeof entry !== 'object') {
        pushIssue(issues, locale, key, 'entry');
        continue;
      }

      if (!entry.label) pushIssue(issues, locale, key, 'label');
      if (!entry.desc) pushIssue(issues, locale, key, 'desc');
      if (!entry.help) pushIssue(issues, locale, key, 'help');

      if (!entry.params || typeof entry.params !== 'object') {
        if (params.length > 0) {
          pushIssue(issues, locale, key, 'params object');
        }
        continue;
      }

      for (const param of params) {
        if (!entry.params[param]) {
          pushIssue(issues, locale, key, 'param', param);
        }
      }
    }
  }

  for (const locale of locales) {
    const keys = Object.keys(localized[locale]);
    for (const key of keys) {
      if (metaKeys.has(key)) continue;
      if (!registry.has(key)) {
        pushIssue(issues, locale, key, 'registry key');
      }
    }
  }

  if (issues.length > 0) {
    console.error('Condition i18n contract check failed.');
    for (const issue of issues) {
      console.error(`- ${issue}`);
    }
    process.exit(1);
  }

  console.log(`Condition i18n contract OK. registry=${registry.size}, locales=${locales.join(',')}`);
}

validate();
