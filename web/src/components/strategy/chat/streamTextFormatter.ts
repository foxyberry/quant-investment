/**
 * Normalize streamed text to prevent excessive whitespace accumulation.
 * - Collapse 3+ consecutive newlines to 2 (preserve paragraph breaks)
 * - Trim trailing whitespace on each line
 * - Normalize Windows-style line endings
 */
export function normalizeStreamText(text: string): string {
  return text
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+$/gm, '')
    .replace(/\n{3,}/g, '\n\n');
}
