'use client';

import { useState, useRef, useEffect, useCallback, KeyboardEvent } from 'react';
import { X, MessageCircle, Send, Loader2, Settings2 } from 'lucide-react';
import { streamPortfolioChat } from '@/lib/api';
import type { ChatMessage } from '@/lib/api';

interface ChatPanelProps {
  /** Whether the chat panel is visible */
  open: boolean;
  /** Callback to close the panel */
  onClose: () => void;
}

interface DisplayMessage {
  role: 'user' | 'assistant';
  content: string;
  /** Unique key for React list rendering */
  id: number;
}

interface ToolActivity {
  name: string;
}

const INITIAL_MESSAGE: DisplayMessage = {
  id: 0,
  role: 'assistant',
  content:
    '안녕하세요! 포트폴리오 분석을 도와드릴게요. 궁금한 종목이나 매매 타이밍을 물어보세요.',
};

/**
 * Minimal inline markdown renderer.
 * Supports **bold**, *italic*, and unordered lists (- or *).
 * No external dependencies.
 */
function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n');
  const result: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];
  let tableRows: string[][] = [];
  let tableHeader: string[] | null = null;
  let nodeKey = 0;

  const flushList = () => {
    if (listItems.length > 0) {
      result.push(
        <ul key={`ul-${nodeKey++}`} className="my-1.5 ml-4 list-disc space-y-0.5 text-sm">
          {listItems}
        </ul>
      );
      listItems = [];
    }
  };

  const flushTable = () => {
    if (tableHeader && tableRows.length > 0) {
      result.push(
        <div key={`tbl-${nodeKey++}`} className="my-2 overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--background)]">
                {tableHeader.map((cell, i) => (
                  <th key={i} className="px-3 py-1.5 text-left font-semibold text-[var(--foreground-muted)]">
                    {parseInline(cell.trim(), nodeKey * 100 + i)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableRows.map((row, ri) => (
                <tr key={ri} className={ri % 2 === 0 ? '' : 'bg-[var(--background)]'}>
                  {row.map((cell, ci) => (
                    <td key={ci} className="px-3 py-1.5 text-[var(--foreground)]">
                      {parseInline(cell.trim(), nodeKey * 100 + ri * 10 + ci)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    tableHeader = null;
    tableRows = [];
  };

  const parseInline = (raw: string, key: number): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*|__)(.+?)\1|(\*|_)(.+?)\3/g;
    let last = 0;
    let m: RegExpExecArray | null;
    let idx = 0;
    while ((m = regex.exec(raw)) !== null) {
      if (m.index > last) {
        parts.push(<span key={`${key}-t${idx++}`}>{raw.slice(last, m.index)}</span>);
      }
      if (m[1]) {
        parts.push(<strong key={`${key}-b${idx++}`} className="font-semibold">{m[2]}</strong>);
      } else {
        parts.push(<em key={`${key}-i${idx++}`}>{m[4]}</em>);
      }
      last = m.index + m[0].length;
    }
    if (last < raw.length) {
      parts.push(<span key={`${key}-t${idx++}`}>{raw.slice(last)}</span>);
    }
    return parts.length === 1 ? parts[0] : <>{parts}</>;
  };

  const parseTableCells = (line: string) =>
    line.replace(/^\||\|$/g, '').split('|');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Heading: ## or ###
    const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)/);
    if (headingMatch) {
      flushList(); flushTable();
      const level = headingMatch[1].length;
      const content = headingMatch[2];
      const cls = level === 1
        ? 'mt-3 mb-1 text-base font-bold text-[var(--foreground)] border-b border-[var(--border)] pb-1'
        : level === 2
        ? 'mt-2.5 mb-1 text-sm font-bold text-[var(--foreground)]'
        : 'mt-2 mb-0.5 text-xs font-semibold text-[var(--foreground-muted)] uppercase tracking-wide';
      result.push(
        <p key={`h${level}-${nodeKey}`} className={cls}>
          {parseInline(content, nodeKey)}
        </p>
      );
      nodeKey++;
      continue;
    }

    // Horizontal rule: --- or ***
    if (/^[-*]{3,}$/.test(trimmed)) {
      flushList(); flushTable();
      result.push(<hr key={`hr-${nodeKey++}`} className="my-2 border-[var(--border)]" />);
      continue;
    }

    // Blockquote: > text
    const bqMatch = trimmed.match(/^>\s*(.*)/);
    if (bqMatch) {
      flushList(); flushTable();
      result.push(
        <blockquote key={`bq-${nodeKey}`} className="my-1 border-l-2 border-[var(--color-primary)] pl-3 text-sm text-[var(--foreground-muted)] italic">
          {parseInline(bqMatch[1], nodeKey)}
        </blockquote>
      );
      nodeKey++;
      continue;
    }

    // Table row: | ... |
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      flushList();
      // Separator row: |---|---|
      if (/^\|[-| :]+\|$/.test(trimmed)) continue;
      const cells = parseTableCells(trimmed);
      if (tableHeader === null) {
        tableHeader = cells;
      } else {
        tableRows.push(cells);
      }
      continue;
    } else {
      flushTable();
    }

    // List item: - or *
    const listMatch = trimmed.match(/^[-*]\s+(.*)/);
    if (listMatch) {
      listItems.push(
        <li key={`li-${nodeKey}`}>{parseInline(listMatch[1], nodeKey)}</li>
      );
      nodeKey++;
      continue;
    }

    flushList();
    if (trimmed === '') {
      result.push(<div key={`sp-${nodeKey++}`} className="h-1" />);
    } else {
      result.push(
        <p key={`p-${nodeKey}`} className="leading-relaxed">
          {parseInline(trimmed, nodeKey)}
        </p>
      );
      nodeKey++;
    }
  }

  flushList();
  flushTable();
  return result;
}

/**
 * Single message bubble in the chat.
 */
function MessageBubble({ msg }: { msg: DisplayMessage }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'rounded-br-sm bg-[var(--color-primary)] text-white'
            : 'rounded-bl-sm bg-[var(--background-secondary)] text-[var(--foreground)]'
        }`}
      >
        {isUser ? (
          <span className="whitespace-pre-wrap">{msg.content}</span>
        ) : (
          <div className="prose-sm">{renderMarkdown(msg.content)}</div>
        )}
      </div>
    </div>
  );
}

/**
 * Animated tool-use indicator shown while the AI calls a tool.
 */
function ToolIndicator({ tool }: { tool: ToolActivity }) {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-xs text-[var(--foreground-muted)]">
        <Settings2 className="h-3.5 w-3.5 animate-spin" />
        <span>{tool.name} 조회 중...</span>
      </div>
    </div>
  );
}

/**
 * AI 어시스턴트 사이드 패널 for portfolio page.
 * Streams responses from POST /api/chat/portfolio.
 */
export default function ChatPanel({ open, onClose }: ChatPanelProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [activeTool, setActiveTool] = useState<ToolActivity | null>(null);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const nextId = useRef(1);
  /** Holds the active AbortController so we can cancel the stream on close/unmount */
  const abortRef = useRef<AbortController | null>(null);

  /** Scroll to the bottom of the message list */
  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeTool, scrollToBottom]);

  /** Focus input when panel opens; abort any running stream when it closes */
  useEffect(() => {
    if (open) {
      // 100 ms delay: allows CSS display transition to complete before focusing
      setTimeout(() => textareaRef.current?.focus(), 100);
    } else {
      abortRef.current?.abort();
    }
  }, [open]);

  /** Cancel any in-flight stream on unmount */
  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

  /** Auto-resize textarea */
  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, []);

  /** Build history for API from display messages (skip greeting + empty bubbles) */
  const buildHistory = useCallback((displayMsgs: DisplayMessage[]): ChatMessage[] => {
    return displayMsgs
      .filter((m) => m.id !== 0 && m.content.trim() !== '')
      .map((m) => ({ role: m.role, content: m.content }));
  }, []);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isSending) return;

    setInput('');
    setError(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const userMsg: DisplayMessage = {
      id: nextId.current++,
      role: 'user',
      content: text,
    };

    const assistantMsg: DisplayMessage = {
      id: nextId.current++,
      role: 'assistant',
      content: '',
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsSending(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const history = buildHistory([...messages, userMsg]);

      const gen = streamPortfolioChat(history, true, controller.signal);
      for await (const event of gen) {
        if (event.type === 'text' && event.content) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, content: m.content + event.content }
                : m
            )
          );
        } else if (event.type === 'tool_start' && event.name) {
          setActiveTool({ name: event.name });
        } else if (event.type === 'tool_end') {
          setActiveTool(null);
        } else if (event.type === 'error' && event.message) {
          setError(event.message);
          setActiveTool(null);
          // Remove empty assistant bubble so it doesn't pollute history on retry
          setMessages((prev) =>
            prev.filter((m) => !(m.id === assistantMsg.id && m.content === ''))
          );
        } else if (event.type === 'done') {
          setActiveTool(null);
        }
      }
    } catch (err) {
      // AbortError is intentional (panel closed) — don't show an error
      if (err instanceof Error && err.name === 'AbortError') {
        setActiveTool(null);
        return;
      }
      setError(err instanceof Error ? err.message : '응답을 불러오지 못했습니다.');
      setActiveTool(null);
      // Remove empty assistant bubble on failure
      setMessages((prev) =>
        prev.filter((m) => !(m.id === assistantMsg.id && m.content === ''))
      );
    } finally {
      setIsSending(false);
    }
  }, [input, isSending, messages, buildHistory]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage]
  );

  // CSS-hide instead of unmount so message history is preserved across open/close
  return (
    <aside
      className={`flex h-full w-[400px] flex-shrink-0 flex-col rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] shadow-xl${!open ? ' hidden' : ''}`}
      aria-label="AI 어시스턴트"
      role="complementary"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="rounded-full bg-blue-100 p-1.5 dark:bg-blue-900/40">
            <MessageCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          </div>
          <span className="text-sm font-semibold text-[var(--foreground)]">AI 어시스턴트</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1 text-[var(--foreground-muted)] transition-colors hover:bg-[var(--border)] hover:text-[var(--foreground)]"
          aria-label="닫기"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Message list */}
      <div
        className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4"
        role="log"
        aria-live="polite"
        aria-label="대화 내용"
      >
        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        {activeTool && <ToolIndicator tool={activeTool} />}
        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
            {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-[var(--border)] px-3 py-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              resizeTextarea();
            }}
            onKeyDown={handleKeyDown}
            disabled={isSending}
            rows={1}
            placeholder="메시지를 입력하세요..."
            aria-label="메시지 입력"
            className="flex-1 resize-none rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:ring-2 focus:ring-blue-500/30 disabled:opacity-50"
            style={{ minHeight: '40px', maxHeight: '120px' }}
          />
          <button
            type="button"
            onClick={sendMessage}
            disabled={isSending || !input.trim()}
            aria-label="전송"
            className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-[var(--color-primary)] text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
        <p className="mt-1.5 text-center text-[10px] text-[var(--foreground-muted)]">
          Enter로 전송 · Shift+Enter 줄바꿈
        </p>
      </div>
    </aside>
  );
}
