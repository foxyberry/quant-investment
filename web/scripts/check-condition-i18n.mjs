import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const repoRoot = path.resolve(process.cwd(), '..');
const messagePaths = {
  en: path.join(process.cwd(), 'messages', 'en.json'),
  ko: path.join(process.cwd(), 'messages', 'ko.json'),
  zh: path.join(process.cwd(), 'messages', 'zh.json'),
};

const metaKeys = new Set(['recommended', 'categories']);

function parseRegistry() {
  const script = [
    'import json',
    'import screener.conditions',
    'from screener.conditions.registry import get_condition_metadata',
    'meta = get_condition_metadata()',
    'result = {k: sorted([p.get("name") for p in v.get("params", []) if isinstance(p, dict) and p.get("name")]) for k, v in meta.items()}',
    'print(json.dumps(result))',
  ].join('; ');

  const pythonBin = process.env.PYTHON_BIN || path.join(repoRoot, 'venv', 'bin', 'python');
  const proc = spawnSync(pythonBin, ['-c', script], {
    cwd: repoRoot,
    encoding: 'utf8',
  });

  if (proc.status !== 0) {
    throw new Error(`Failed to load condition registry: ${proc.stderr || proc.stdout}`);
  }

  const parsed = JSON.parse(proc.stdout.trim() || '{}');
  return new Map(Object.entries(parsed));
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
