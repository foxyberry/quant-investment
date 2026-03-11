'use client';

import { memo, useState, useCallback } from 'react';
import { Copy, Check, ClipboardCheck, Loader2 } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

interface StructuredSuggestion {
  condition_type: string;
  params: Record<string, unknown>;
  rationale: string;
}

interface StructuredPayload {
  summary?: string;
  suggestions?: StructuredSuggestion[];
  warnings?: string[];
}

interface MessageActionsProps {
  content: string;
  payload?: StructuredPayload;
}

function MessageActions({ content, payload }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<
    { allValid: boolean; errors: string[] } | null
  >(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for browsers that don't support clipboard API
    }
  }, [content]);

  const handleValidate = useCallback(async () => {
    if (!payload?.suggestions?.length) return;
    setValidating(true);
    setValidationResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/strategy/chat/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          suggestions: payload.suggestions.map(s => ({
            condition_type: s.condition_type,
            params: s.params && typeof s.params === 'object' && !Array.isArray(s.params)
              ? s.params
              : {},
          })),
        }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      const errors: string[] = [];
      for (const r of data.results) {
        if (!r.valid) {
          for (const e of r.errors) {
            errors.push(`${r.condition_type}.${e.param}: ${e.message}`);
          }
        }
      }
      setValidationResult({ allValid: data.all_valid, errors });
    } catch {
      setValidationResult({ allValid: false, errors: ['Validation request failed'] });
    } finally {
      setValidating(false);
    }
  }, [payload]);

  const hasSuggestions = payload?.suggestions && payload.suggestions.length > 0;

  return (
    <div className="mt-1">
      <div className="flex items-center gap-1">
        {/* Copy button */}
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
          title="Copy message"
        >
          {copied ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
          {copied ? 'Copied' : 'Copy'}
        </button>

        {/* Validate button — only when suggestions exist */}
        {hasSuggestions && (
          <button
            type="button"
            onClick={handleValidate}
            disabled={validating}
            className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:opacity-50 dark:hover:bg-gray-800 dark:hover:text-gray-300"
            title="Validate conditions"
          >
            {validating ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <ClipboardCheck className="h-3 w-3" />
            )}
            Validate
          </button>
        )}
      </div>

      {/* Validation result */}
      {validationResult && (
        <div
          className={`mt-1 rounded px-2 py-1 text-[10px] ${
            validationResult.allValid
              ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
              : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
          }`}
        >
          {validationResult.allValid ? (
            'All conditions are valid'
          ) : (
            <ul className="list-inside list-disc space-y-0.5">
              {validationResult.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(MessageActions);
