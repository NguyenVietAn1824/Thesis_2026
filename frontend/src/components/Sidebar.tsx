'use client';

import type { Conversation } from '@/types';

interface Props {
  open: boolean;
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  userId: string;
}

export default function Sidebar({
  open,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  userId,
}: Props) {
  if (!open) return null;

  return (
    <aside className="flex h-full w-[260px] flex-shrink-0 flex-col bg-[#171717]">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3">
        <div className="flex items-center gap-2 px-2">
          <AirIcon />
          <span className="text-sm font-semibold text-[#ececec]">AQI Agent</span>
        </div>
        <button
          onClick={onNewChat}
          title="New chat"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[#8e8ea0] transition hover:bg-[#2a2a2a] hover:text-[#ececec]"
        >
          <PencilIcon />
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 ? (
          <p className="px-3 py-3 text-xs text-[#5a5a5a]">No conversations yet</p>
        ) : (
          <>
            <p className="px-3 py-1.5 text-xs font-medium text-[#5a5a5a]">Recent</p>
            <div className="space-y-0.5">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => onSelectConversation(conv.id)}
                  className={`group flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition ${
                    conv.id === activeConversationId
                      ? 'bg-[#2f2f2f] text-[#ececec]'
                      : 'text-[#b0b0b0] hover:bg-[#212121] hover:text-[#ececec]'
                  }`}
                >
                  <ChatBubbleIcon className="flex-shrink-0 text-[#5a5a5a]" />
                  <span className="flex-1 truncate">{conv.title}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Footer - user */}
      <div className="border-t border-[#2a2a2a] px-3 py-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-1.5">
          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-emerald-600 text-xs font-bold text-white">
            {userId.charAt(0).toUpperCase()}
          </div>
          <span className="truncate text-sm text-[#c5c5c5]">{userId}</span>
        </div>
      </div>
    </aside>
  );
}

function AirIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path
        d="M9.59 4.59A2 2 0 1111 8H2m10.59 11.41A2 2 0 1014 16H2m15.73-8.27A2.5 2.5 0 1119.5 12H2"
        stroke="#34d399"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

function ChatBubbleIcon({ className }: { className?: string }) {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
    </svg>
  );
}
