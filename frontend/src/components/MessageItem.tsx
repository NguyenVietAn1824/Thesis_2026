'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '@/types';

interface Props {
  message: Message;
}

export default function MessageItem({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end px-4 md:px-6">
        <div className="max-w-[75%]">
          <div className="rounded-2xl rounded-tr-sm bg-[#2f2f2f] px-4 py-3 text-sm leading-relaxed text-[#ececec]">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 px-4 md:px-6">
      <div className="mt-0.5 flex-shrink-0">
        <AgentAvatar />
      </div>
      <div className="min-w-0 flex-1">
        {message.isLoading ? (
          <LoadingDots />
        ) : (
          <div
            className={`text-sm ${message.isError ? 'text-red-300' : 'text-[#e0e0e0]'}`}
          >
            <div className="markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
        )}
        {!message.isLoading && (
          <div className="mt-1.5 text-xs text-[#5a5a5a]">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function AgentAvatar() {
  return (
    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-600">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <path
          d="M9.59 4.59A2 2 0 1111 8H2m10.59 11.41A2 2 0 1014 16H2m15.73-8.27A2.5 2.5 0 1119.5 12H2"
          stroke="white"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function LoadingDots() {
  return (
    <div className="flex items-center gap-1.5 py-1.5">
      <span className="dot-1 h-2 w-2 rounded-full bg-[#6b6b6b]" />
      <span className="dot-2 h-2 w-2 rounded-full bg-[#6b6b6b]" />
      <span className="dot-3 h-2 w-2 rounded-full bg-[#6b6b6b]" />
    </div>
  );
}
