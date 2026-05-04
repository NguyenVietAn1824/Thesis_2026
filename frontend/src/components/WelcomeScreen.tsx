'use client';

const SUGGESTIONS = [
  {
    icon: '🌬️',
    title: 'Current AQI',
    prompt: 'What is the current AQI level across Hanoi districts?',
  },
  {
    icon: '📍',
    title: 'Worst areas',
    prompt: 'Which districts in Hanoi have the highest pollution right now?',
  },
  {
    icon: '📈',
    title: 'Weekly trend',
    prompt: 'Show me the air quality trend in Hanoi for the past 7 days.',
  },
  {
    icon: '✅',
    title: 'Safe to go outside?',
    prompt: 'Which areas in Hanoi have good air quality today?',
  },
];

interface Props {
  onSuggestionClick: (prompt: string) => void;
}

export default function WelcomeScreen({ onSuggestionClick }: Props) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6">
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
            <path
              d="M9.59 4.59A2 2 0 1111 8H2m10.59 11.41A2 2 0 1014 16H2m15.73-8.27A2.5 2.5 0 1119.5 12H2"
              stroke="#34d399"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-semibold text-[#ececec]">How can I help you?</h1>
        <p className="text-sm text-[#8e8ea0]">
          Ask me anything about air quality in Hanoi
        </p>
      </div>

      <div className="grid w-full max-w-2xl grid-cols-2 gap-3">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.title}
            onClick={() => onSuggestionClick(s.prompt)}
            className="rounded-xl border border-[#3f3f3f] bg-[#2a2a2a] p-4 text-left transition hover:border-[#5a5a5a] hover:bg-[#333333] active:scale-[0.98]"
          >
            <div className="mb-1.5 text-xl">{s.icon}</div>
            <div className="mb-0.5 text-sm font-medium text-[#ececec]">{s.title}</div>
            <div className="line-clamp-2 text-xs text-[#8e8ea0]">{s.prompt}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
