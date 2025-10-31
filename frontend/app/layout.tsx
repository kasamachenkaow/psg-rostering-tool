import type { Metadata } from 'next';
import './globals.css';
import { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'PSG Rostering Command Center',
  description: 'Holographic mission control for PSG rostering intelligence.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased holo-grid">
        <div className="min-h-screen bg-night/80 backdrop-blur-xl">
          {children}
        </div>
      </body>
    </html>
  );
}
