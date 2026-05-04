'use client';

import { useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import Sidebar from '@/components/Sidebar';
import ChatWindow from '@/components/ChatWindow';
import UserSetupModal from '@/components/UserSetupModal';
import type { Conversation, Message } from '@/types';

const API_URL = '/proxy/v1/aqi_agent';

export default function Home() {
  const [userId, setUserId] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const activeConversation = conversations.find((c) => c.id === activeConversationId) ?? null;

  const handleNewChat = useCallback(() => {
    setActiveConversationId(null);
  }, []);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || isLoading) return;

      let convId = activeConversationId;

      if (!convId) {
        convId = uuidv4();
        const title = question.length > 48 ? question.slice(0, 48) + '…' : question;
        setConversations((prev) => [
          { id: convId!, title, messages: [], createdAt: new Date() },
          ...prev,
        ]);
        setActiveConversationId(convId);
      }

      const userMsg: Message = {
        id: uuidv4(),
        role: 'user',
        content: question,
        timestamp: new Date(),
      };
      const loadingMsg: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isLoading: true,
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? { ...c, messages: [...c.messages, userMsg, loadingMsg] }
            : c,
        ),
      );
      setIsLoading(true);

      try {
        const res = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question,
            conversation_id: convId,
            user_id: userId,
          }),
        });

        if (!res.ok) {
          const text = await res.text().catch(() => '');
          throw new Error(text || `HTTP ${res.status}`);
        }

        const data: { info: { response: string } } = await res.json();

        setConversations((prev) =>
          prev.map((c) =>
            c.id === convId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.isLoading
                      ? { ...m, content: data.info.response, isLoading: false }
                      : m,
                  ),
                }
              : c,
          ),
        );
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : 'An unexpected error occurred.';
        setConversations((prev) =>
          prev.map((c) =>
            c.id === convId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.isLoading
                      ? {
                          ...m,
                          content: `**Could not reach the AQI Agent service.**\n\n${msg}\n\nMake sure the service is running on port 3334.`,
                          isLoading: false,
                          isError: true,
                        }
                      : m,
                  ),
                }
              : c,
          ),
        );
      } finally {
        setIsLoading(false);
      }
    },
    [activeConversationId, isLoading, userId],
  );

  if (!userId) {
    return <UserSetupModal onSetup={setUserId} />;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        open={sidebarOpen}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewChat={handleNewChat}
        userId={userId}
      />
      <ChatWindow
        conversation={activeConversation}
        isLoading={isLoading}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((o) => !o)}
        onSendMessage={sendMessage}
        onSuggestionClick={sendMessage}
      />
    </div>
  );
}
