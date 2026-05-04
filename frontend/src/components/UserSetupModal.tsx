'use client';

import { useState } from 'react';

interface Props {
  onSetup: (userId: string) => void;
}

export default function UserSetupModal({ onSetup }: Props) {
  const [userId, setUserId] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = userId.trim();
    if (!trimmed) {
      setError('Please enter a user ID');
      return;
    }
    onSetup(trimmed);
  };

  return (
    <div className="flex h-screen items-center justify-center bg-[#212121]">
      <div className="w-full max-w-sm rounded-2xl border border-[#3f3f3f] bg-[#2a2a2a] p-8 shadow-2xl">
        <div className="mb-7 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/15">
            <AirIcon />
          </div>
          <h1 className="text-xl font-semibold text-[#ececec]">Welcome to AQI Agent</h1>
          <p className="text-center text-sm text-[#8e8ea0]">
            Your AI assistant for Hanoi air quality data
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-[#c5c5c5]">Email</label>
            <input
              type="email"
              value={userId}
              onChange={(e) => {
                setUserId(e.target.value);
                setError('');
              }}
              placeholder="Enter your email"
              autoFocus
              className="w-full rounded-xl border border-[#3f3f3f] bg-[#171717] px-4 py-2.5 text-sm text-[#ececec] placeholder:text-[#5a5a5a] transition focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
            {error && <p className="mt-1.5 text-xs text-red-400">{error}</p>}
          </div>
          <button
            type="submit"
            className="w-full rounded-xl bg-emerald-600 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 active:bg-emerald-700"
          >
            Get started
          </button>
        </form>
      </div>
    </div>
  );
}

function AirIcon() {
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none">
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
