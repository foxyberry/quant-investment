'use client';

import { useCallback, useEffect, useState } from 'react';
import { X } from 'lucide-react';

export type ToastType = 'error' | 'warning' | 'info' | 'success';

interface ToastProps {
  message: string;
  type: ToastType;
  onClose: () => void;
}

const toastStyles: Record<ToastType, string> = {
  error: 'bg-red-500',
  warning: 'bg-amber-500',
  info: 'bg-[#1313ec]',
  success: 'bg-emerald-500',
};

export function Toast({ message, type, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const enterTimer = window.setTimeout(() => setIsVisible(true), 10);
    const dismissTimer = window.setTimeout(onClose, 3000);

    return () => {
      window.clearTimeout(enterTimer);
      window.clearTimeout(dismissTimer);
    };
  }, [onClose]);

  return (
    <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2">
      <div
        className={`${toastStyles[type]} flex min-w-[280px] items-center gap-3 rounded-lg px-4 py-3 text-white shadow-lg transition-all duration-300 ease-out ${
          isVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
        role="status"
        aria-live="polite"
      >
        <span className="flex-1 text-sm">{message}</span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close toast"
          className="rounded p-1 text-white/90 transition hover:bg-white/20 hover:text-white"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

interface ToastState {
  message: string;
  type: string;
}

export function useToast() {
  const [toast, setToast] = useState<ToastState | null>(null);

  const showToast = useCallback((message: string, type: ToastType) => {
    setToast({ message, type });
  }, []);

  const hideToast = useCallback(() => {
    setToast(null);
  }, []);

  return { toast, showToast, hideToast };
}
