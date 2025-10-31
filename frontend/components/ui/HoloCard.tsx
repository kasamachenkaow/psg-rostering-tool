'use client';

import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface HoloCardProps {
  title?: string;
  subtitle?: string;
  className?: string;
  glow?: 'cyan' | 'indigo' | 'blue';
  children: ReactNode;
}

const glowMap: Record<NonNullable<HoloCardProps['glow']>, string> = {
  cyan: 'from-neon-cyan/60 via-neon-blue/10 to-transparent',
  indigo: 'from-neon-indigo/50 via-neon-blue/20 to-transparent',
  blue: 'from-holo-200/60 via-holo-400/20 to-transparent',
};

export function HoloCard({ title, subtitle, className, glow = 'cyan', children }: HoloCardProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={clsx(
        'relative overflow-hidden rounded-3xl border border-holo-400/40 bg-slate-900/40 p-6 shadow-holo backdrop-blur-xl',
        'before:absolute before:inset-0 before:-z-10 before:bg-gradient-to-br before:opacity-60',
        'after:pointer-events-none after:absolute after:inset-6 after:rounded-2xl after:border after:border-cyan-400/20 after:opacity-40',
        className
      )}
    >
      <div className={clsx('absolute inset-0 -z-20 bg-gradient-to-br blur-2xl', glowMap[glow])} />
      {title && (
        <header className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="font-display text-xl tracking-[0.3em] text-neon-cyan uppercase">{title}</h2>
            {subtitle && <p className="text-xs text-slate-300/80">{subtitle}</p>}
          </div>
          <div className="h-8 w-8 rounded-full border border-cyan-300/40 bg-cyan-300/10 shadow-inset" />
        </header>
      )}
      <div className="relative z-10 space-y-4">{children}</div>
    </motion.section>
  );
}
