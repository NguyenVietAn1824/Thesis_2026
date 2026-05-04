'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface Props {
  onSend: (message: string) => void;
  isLoading: boolean;
}

export default function InputBar({ onSend, isLoading }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }, [value]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, isLoading, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = value.trim().length > 0 && !isLoading;

  return (
    <div className="flex-shrink-0 px-4 pb-5 pt-2">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-3 rounded-2xl border border-[#3f3f3f] bg-[#2f2f2f] px-4 py-3 shadow-lg transition focus-within:border-[#5a5a5a]">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about air quality in Hanoi…"
            rows={1}
            disabled={isLoading}
            className="flex-1 resize-none bg-transparent text-sm leading-relaxed text-[#ececec] placeholder:text-[#5a5a5a] focus:outline-none disabled:opacity-50"
            style={{ maxHeight: '200px' }}
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            className={`mb-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg transition ${
              canSend
                ? 'bg-emerald-600 hover:bg-emerald-500 active:scale-95'
                : 'cursor-not-allowed bg-[#3f3f3f]'
            }`}
          >
            <SendIcon active={canSend} />
          </button>
        </div>
        <p className="mt-2 text-center text-xs text-[#4a4a4a]">
          AQI Agent can make mistakes. Verify important air quality data.
        </p>
      </div>
    </div>
  );
}

function SendIcon({ active }: { active: boolean }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path
        d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"
        stroke={active ? 'white' : '#5a5a5a'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
