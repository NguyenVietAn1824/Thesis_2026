'use client';

import { useEffect, useRef } from 'react';
import type { Conversation } from '@/types';
import WelcomeScreen from './WelcomeScreen';
import MessageItem from './MessageItem';
import InputBar from './InputBar';

interface Props {
  conversation: Conversation | null;
  isLoading: boolean;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  onSendMessage: (msg: string) => void;
  onSuggestionClick: (prompt: string) => void;
}

export default function ChatWindow({
  conversation,
  isLoading,
  sidebarOpen,
  onToggleSidebar,
  onSendMessage,
  onSuggestionClick,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation?.messages]);

  const messages = conversation?.messages ?? [];

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Top bar */}
      <header className="flex h-12 flex-shrink-0 items-center gap-2 border-b border-[#2a2a2a] px-4">
        <button
          onClick={onToggleSidebar}
          title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6b6b6b] transition hover:bg-[#2f2f2f] hover:text-[#ececec]"
        >
          <MenuIcon />
        </button>
        <span className="truncate text-sm text-[#8e8ea0]">
          {conversation?.title ?? 'New chat'}
        </span>
      </header>

      {/* Content */}
      <div className="flex flex-1 flex-col overflow-y-auto">
        {messages.length === 0 ? (
          <WelcomeScreen onSuggestionClick={onSuggestionClick} />
        ) : (
          <div className="mx-auto w-full max-w-3xl space-y-6 py-6">
            {messages.map((msg) => (
              <MessageItem key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <InputBar onSend={onSendMessage} isLoading={isLoading} />
    </div>
  );
}

function MenuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M3 12h18M3 6h18M3 18h18" />
    </svg>
  );
}
