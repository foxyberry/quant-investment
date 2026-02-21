'use client';

import { useState, useCallback, useRef } from 'react';
import { X, Upload, Download, AlertTriangle, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui';
import { importHoldingsCsv, downloadHoldingsTemplate } from '@/lib/api';
import type { CsvImportResponse } from '@/lib/types';

interface CsvImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportComplete: () => void;
}

export default function CsvImportModal({ isOpen, onClose, onImportComplete }: CsvImportModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<'merge' | 'replace'>('merge');
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [result, setResult] = useState<CsvImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetState = useCallback(() => {
    setFile(null);
    setMode('merge');
    setIsUploading(false);
    setIsDragging(false);
    setResult(null);
    setError(null);
  }, []);

  const handleClose = useCallback(() => {
    if (isUploading) return;
    resetState();
    onClose();
  }, [isUploading, resetState, onClose]);

  const handleFile = useCallback((f: File) => {
    if (!f.name.endsWith('.csv')) {
      setError('Please select a CSV file.');
      return;
    }
    if (f.size > 1_048_576) {
      setError('File too large (max 1 MB).');
      return;
    }
    setFile(f);
    setError(null);
    setResult(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleImport = useCallback(async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);

    try {
      const res = await importHoldingsCsv(file, mode);
      setResult(res);
      onImportComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setIsUploading(false);
    }
  }, [file, mode, onImportComplete]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
        onKeyDown={(e) => e.key === 'Escape' && handleClose()}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 rounded-lg border border-[var(--border)] bg-[var(--background)] shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            Import Holdings from CSV
          </h2>
          <button
            onClick={handleClose}
            disabled={isUploading}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--background-secondary)] hover:text-[var(--foreground)]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {/* Drop zone */}
          {!result && (
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 cursor-pointer transition-colors ${
                isDragging
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/5'
                  : file
                  ? 'border-green-500 bg-green-50 dark:bg-green-950/20'
                  : 'border-[var(--border)] hover:border-[var(--foreground-muted)]'
              }`}
            >
              <Upload className={`h-8 w-8 ${file ? 'text-green-600' : 'text-[var(--foreground-muted)]'}`} />
              {file ? (
                <p className="text-sm text-green-700 dark:text-green-400 font-medium">{file.name}</p>
              ) : (
                <>
                  <p className="text-sm text-[var(--foreground-muted)]">
                    Drop CSV file here or click to browse
                  </p>
                  <p className="text-xs text-[var(--foreground-muted)]">Max 1 MB</p>
                </>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFile(f);
                }}
              />
            </div>
          )}

          {/* Mode selector */}
          {!result && (
            <div>
              <label className="block text-sm font-medium text-[var(--foreground)] mb-2">
                Import Mode
              </label>
              <div className="flex gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="mode"
                    value="merge"
                    checked={mode === 'merge'}
                    onChange={() => setMode('merge')}
                    className="accent-[var(--color-primary)]"
                  />
                  <span className="text-sm text-[var(--foreground)]">Merge</span>
                  <span className="text-xs text-[var(--foreground-muted)]">(update existing, add new)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="mode"
                    value="replace"
                    checked={mode === 'replace'}
                    onChange={() => setMode('replace')}
                    className="accent-[var(--color-primary)]"
                  />
                  <span className="text-sm text-[var(--foreground)]">Replace</span>
                  <span className="text-xs text-[var(--foreground-muted)]">(clear all first)</span>
                </label>
              </div>
              {mode === 'replace' && (
                <div className="mt-2 flex items-start gap-2 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-amber-800 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                  <p className="text-xs">This will delete all existing holdings before importing.</p>
                </div>
              )}
            </div>
          )}

          {/* Template download */}
          {!result && (
            <div className="flex items-center gap-2">
              <Download className="h-4 w-4 text-[var(--foreground-muted)]" />
              <button
                onClick={() => downloadHoldingsTemplate(false)}
                className="text-sm text-[var(--color-primary)] hover:underline"
              >
                Download template
              </button>
              <span className="text-[var(--foreground-muted)]">|</span>
              <button
                onClick={() => downloadHoldingsTemplate(true)}
                className="text-sm text-[var(--color-primary)] hover:underline"
              >
                Minimal template
              </button>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300">
              {error}
            </div>
          )}

          {/* Result */}
          {result && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                <CheckCircle className="h-5 w-5" />
                <span className="font-medium">Import completed</span>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="rounded-lg bg-[var(--background-secondary)] p-3">
                  <p className="text-2xl font-semibold text-[var(--foreground)]">{result.imported}</p>
                  <p className="text-xs text-[var(--foreground-muted)]">Created</p>
                </div>
                <div className="rounded-lg bg-[var(--background-secondary)] p-3">
                  <p className="text-2xl font-semibold text-[var(--foreground)]">{result.updated}</p>
                  <p className="text-xs text-[var(--foreground-muted)]">Updated</p>
                </div>
                <div className="rounded-lg bg-[var(--background-secondary)] p-3">
                  <p className="text-2xl font-semibold text-[var(--foreground)]">{result.skipped}</p>
                  <p className="text-xs text-[var(--foreground-muted)]">Skipped</p>
                </div>
              </div>
              {result.errors.length > 0 && (
                <div className="rounded border border-amber-300 bg-amber-50 p-3 dark:border-amber-700 dark:bg-amber-950/30">
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-300 mb-1">
                    {result.errors.length} error(s)
                  </p>
                  <ul className="space-y-1">
                    {result.errors.map((err, i) => (
                      <li key={i} className="text-xs text-amber-700 dark:text-amber-400">
                        Row {err.row}{err.ticker ? ` (${err.ticker})` : ''}: {err.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t border-[var(--border)] px-6 py-4">
          {result ? (
            <Button variant="primary" onClick={handleClose}>
              Done
            </Button>
          ) : (
            <>
              <Button variant="outline" onClick={handleClose} disabled={isUploading}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleImport}
                disabled={!file || isUploading}
                isLoading={isUploading}
              >
                {isUploading ? 'Importing...' : 'Import'}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
