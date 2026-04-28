'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { MessageCircle, X, Send, Loader2, User, Bot } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import MarkdownMessage from './chat/MarkdownMessage';
import MessageActions from './chat/MessageActions';
import SectionedMessage from './chat/SectionedMessage';
import { normalizeChunk, finalizeStreamText } from './chat/streamTextFormatter';
import { cn } from '@/lib/utils';

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

export interface NodeMapping {
  condition_type: string;
  node_type: string;
  params: Record<string, unknown>;
  label: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  structuredPayload?: StructuredPayload;
  nodeMappings?: NodeMapping[];
}

export interface ExistingConditionNode {
  id: string;
  condition_type: string;
}

interface ChatPanelProps {
  graph: { nodes: unknown[]; edges: unknown[] } | null;
  onAddNodes?: (nodes: NodeMapping[]) => void;
  existingConditionNodes?: ExistingConditionNode[];
  onUpdateNode?: (nodeId: string, params: Record<string, unknown>) => void;
}

export default function ChatPanel({ graph, onAddNodes, existingConditionNodes, onUpdateNode }: ChatPanelProps) {
  const t = useTranslations('strategy');
  const locale = useLocale();

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const chatTitle = t.has('chatbot.title') ? t('chatbot.title') : 'AI Strategy Assistant';
  const chatPlaceholder = t.has('chatbot.placeholder')
    ? t('chatbot.placeholder')
    : 'Ask about your strategy...';
  const chatError = t.has('chatbot.error')
    ? t('chatbot.error')
    : 'Failed to get response. Please try again.';
  const chatEmpty = t.has('chatbot.empty')
    ? t('chatbot.empty')
    : 'Ask me anything about building your strategy.';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen) textareaRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

  const sendMessage = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: trimmed };
    const newMessages = [...messages, userMsg];
    setMessages([...newMessages, { id: crypto.randomUUID(), role: 'assistant', content: '' }]);
    setInput('');
    setIsStreaming(true);

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(`${API_BASE_URL}/api/strategy/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages, graph, locale }),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error(`API Error: ${response.status}`);

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      const processLines = (lines: string[]) => {
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'chunk' && data.content) {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === 'assistant') {
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + normalizeChunk(data.content),
                  };
                }
                return updated;
              });
            } else if (data.type === 'structured_payload' && data.payload) {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === 'assistant') {
                  updated[updated.length - 1] = {
                    ...last,
                    content: data.clean_text || last.content.replace(/<!--\s*STRUCTURED_JSON[\s\S]*?-->/g, '').trimEnd(),
                    structuredPayload: data.payload,
                    nodeMappings: data.node_mappings || undefined,
                  };
                }
                return updated;
              });
            } else if (data.type === 'error') {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === 'assistant') {
                  updated[updated.length - 1] = { ...last, content: chatError };
                }
                return updated;
              });
            }
          } catch {
            // ignore parse errors (heartbeats, etc.)
          }
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        processLines(lines);
      }

      buffer += decoder.decode(new Uint8Array(), { stream: false });
      if (buffer.trim()) processLines(buffer.split('\n'));
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === 'assistant' && !last.content) {
          updated[updated.length - 1] = { ...last, content: chatError };
        }
        return updated;
      });
    } finally {
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === 'assistant' && last.content) {
          updated[updated.length - 1] = { ...last, content: finalizeStreamText(last.content) };
        }
        return updated;
      });
      setIsStreaming(false);
    }
  }, [input, isStreaming, messages, graph, locale, chatError]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage],
  );

  return (
    <>
      {/* Floating bubble */}
      <button
        type="button"
        onClick={() => setIsOpen(prev => !prev)}
        className="fixed bottom-20 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        aria-label={isOpen ? 'Close chat' : 'Open chat'}
      >
        {isOpen ? <X className="h-5 w-5" /> : <MessageCircle className="h-5 w-5" />}
      </button>

      {/* Chat panel */}
      {isOpen && (
        <div
          className="fixed bottom-36 right-6 z-50 flex h-[500px] w-[380px] flex-col rounded-xl border border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-900"
          role="dialog"
          aria-label={chatTitle}
        >
          {/* Header */}
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-gray-200 px-4 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {chatTitle}
            </h3>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="rounded p-1 transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
              aria-label="Close"
            >
              <X className="h-4 w-4 text-gray-400" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3">
            {messages.length === 0 && (
              <div className="flex h-full items-center justify-center">
                <p className="text-center text-sm text-gray-400 dark:text-gray-500">
                  {chatEmpty}
                </p>
              </div>
            )}
            <div className="flex flex-col gap-4">
              {messages.map((msg, i) => (
                <div
                  key={msg.id}
                  aria-label={msg.role === 'user' ? 'You' : 'AI Assistant'}
                  className={`flex items-end gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  {/* Avatar */}
                  <div
                    aria-hidden="true"
                    className={cn(
                      'flex-shrink-0 flex h-7 w-7 items-center justify-center rounded-full text-white shadow-sm',
                      msg.role === 'user'
                        ? 'bg-blue-600'
                        : 'bg-gradient-to-br from-violet-500 to-indigo-600',
                    )}
                  >
                    {msg.role === 'user'
                      ? <User className="h-3.5 w-3.5" />
                      : <Bot className="h-3.5 w-3.5" />
                    }
                  </div>

                  {/* Bubble wrapper */}
                  <div className={`flex max-w-[75%] flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div
                      className={cn(
                        'rounded-2xl px-3 py-2.5 text-sm leading-relaxed',
                        msg.role === 'user'
                          ? 'rounded-br-sm bg-blue-600 text-white whitespace-pre-wrap'
                          : 'rounded-bl-sm bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100',
                      )}
                    >
                      {msg.role === 'user' ? (
                        msg.content
                      ) : msg.structuredPayload ? (
                        <SectionedMessage
                          content={msg.content}
                          payload={msg.structuredPayload}
                          nodeMappings={msg.nodeMappings}
                          onAddNodes={onAddNodes}
                          existingConditionNodes={existingConditionNodes}
                          onUpdateNode={onUpdateNode}
                        />
                      ) : (
                        <MarkdownMessage content={msg.content} />
                      )}
                      {msg.role === 'assistant' && i === messages.length - 1 && isStreaming && (
                        msg.content
                          ? <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-current align-text-bottom" />
                          : <Loader2 className="inline h-3 w-3 animate-spin text-gray-400" />
                      )}
                    </div>
                    {msg.role === 'assistant' &&
                      msg.content &&
                      !(i === messages.length - 1 && isStreaming) && (
                        <MessageActions
                          content={msg.content}
                          payload={msg.structuredPayload}
                        />
                      )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input */}
          <div className="flex h-14 shrink-0 items-center gap-2 border-t border-gray-200 px-3 dark:border-gray-700">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isStreaming}
              placeholder={chatPlaceholder}
              rows={1}
              className="flex-1 resize-none rounded-lg border border-gray-200 bg-transparent px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none transition-colors focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-blue-400"
            />
            <button
              type="button"
              onClick={sendMessage}
              disabled={isStreaming || !input.trim()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Send"
            >
              {isStreaming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
