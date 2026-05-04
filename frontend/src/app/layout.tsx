import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AQI Agent',
  description: 'AI assistant for Hanoi air quality data',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#212121] text-[#ececec] antialiased">{children}</body>
    </html>
  );
}
