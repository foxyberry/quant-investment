'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { searchTickers } from '@/lib/api';

interface SearchResult {
  ticker: string;
  name: string;
}

interface TickerSearchInputProps {
  value: string;
  onChange: (ticker: string, name?: string) => void;
  placeholder?: string;
  disabled?: boolean;
  hasError?: boolean;
  autoFocus?: boolean;
  id?: string;
  /** Ref forwarded to the underlying input element */
  inputRef?: React.RefObject<HTMLInputElement | null>;
}

/**
 * Ticker input with autocomplete search dropdown.
 * Searches by stock name (Korean/English) or ticker symbol.
 * On select, fills the ticker field and optionally returns the stock name.
 */
export default function TickerSearchInput({
  value,
  onChange,
  placeholder = 'e.g., AAPL',
  disabled = false,
  hasError = false,
  autoFocus = false,
  id,
  inputRef: externalRef,
}: TickerSearchInputProps) {
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const internalRef = useRef<HTMLInputElement>(null);
  const inputElement = externalRef || internalRef;
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  // Sync external value changes
  useEffect(() => {
    setQuery(value);
  }, [value]);

  const doSearch = useCallback(async (q: string) => {
    if (q.trim().length < 1) {
      setResults([]);
      setIsOpen(false);
      return;
    }
    setIsLoading(true);
    try {
      const data = await searchTickers(q.trim());
      setResults(data.slice(0, 10));
      setIsOpen(data.length > 0);
      setActiveIndex(-1);
    } catch {
      setResults([]);
      setIsOpen(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    onChange(val);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val), 300);
  };

  const handleSelect = (result: SearchResult) => {
    setQuery(result.ticker);
    onChange(result.ticker, result.name);
    setIsOpen(false);
    setResults([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || results.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      handleSelect(results[activeIndex]);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div ref={containerRef} className="relative">
      <input
        ref={inputElement}
        type="text"
        id={id}
        value={query}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => { if (results.length > 0) setIsOpen(true); }}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        autoComplete="off"
        className={`w-full rounded-lg border px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] ${
          hasError ? 'border-red-500' : 'border-[var(--border)]'
        }`}
      />

      {isLoading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--foreground-muted)] border-t-transparent" />
        </div>
      )}

      {isOpen && results.length > 0 && (
        <ul
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-lg"
          role="listbox"
        >
          {results.map((result, index) => (
            <li
              key={result.ticker}
              role="option"
              aria-selected={index === activeIndex}
              onClick={() => handleSelect(result)}
              onMouseEnter={() => setActiveIndex(index)}
              className={`cursor-pointer px-3 py-2 text-sm ${
                index === activeIndex
                  ? 'bg-[var(--color-primary)]/10 text-[var(--foreground)]'
                  : 'text-[var(--foreground)] hover:bg-[var(--border)]/50'
              }`}
            >
              <span className="font-mono font-semibold">{result.ticker}</span>
              <span className="ml-2 text-[var(--foreground-muted)]">{result.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
