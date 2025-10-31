'use client';

import clsx from 'clsx';

interface ToggleSwitchProps {
  id: string;
  label: string;
  description?: string;
  value: boolean;
  onChange: (next: boolean) => void;
}

export function ToggleSwitch({ id, label, description, value, onChange }: ToggleSwitchProps) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={clsx(
        'relative flex w-full items-center justify-between rounded-2xl border border-holo-400/40 bg-slate-900/40 p-4 transition-all',
        'hover:border-neon-cyan/60 hover:shadow-holo focus:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan/80',
        value ? 'shadow-holo' : 'opacity-80'
      )}
      aria-pressed={value}
      aria-labelledby={`${id}-label`}
    >
      <div className="text-left">
        <span id={`${id}-label`} className="font-display text-sm uppercase tracking-[0.3em] text-slate-100">
          {label}
        </span>
        {description && <p className="mt-1 text-xs text-slate-300/80">{description}</p>}
      </div>
      <span
        className={clsx(
          'relative inline-flex h-8 w-16 items-center rounded-full border border-cyan-400/40 bg-slate-800/70 p-1 transition-colors',
          value ? 'bg-gradient-to-r from-neon-cyan/60 to-neon-blue/40' : 'bg-slate-800/80'
        )}
      >
        <span
          className={clsx(
            'h-6 w-6 rounded-full bg-white/90 shadow-holo transition-transform',
            value ? 'translate-x-8 bg-neon-cyan' : 'translate-x-0 bg-slate-500'
          )}
        />
      </span>
    </button>
  );
}
