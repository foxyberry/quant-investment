/**
 * Normalize streamed text to prevent excessive whitespace accumulation.
 * - Collapse 3+ consecutive newlines to 2 (preserve paragraph breaks)
 * - Trim trailing whitespace on each line, preserving markdown hard breaks (2+ trailing spaces)
 * - Normalize Windows-style line endings
 */
export function normalizeStreamText(text: string): string {
  return text
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]{3,}$/gm, '  ')
    .replace(/\n{3,}/g, '\n\n');
}

/**
 * Lightweight normalizer for appending a single chunk.
 * Only fixes CRLF in the new chunk to avoid O(n²) full-text passes.
 * Full normalization is applied once at stream end.
 */
export function normalizeChunk(chunk: string): string {
  return chunk.replace(/\r\n/g, '\n');
}

/**
 * Final normalization pass applied once when streaming completes.
 */
export function finalizeStreamText(text: string): string {
  return normalizeStreamText(text);
}
