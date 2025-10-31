'use client';

import { ChangeEvent, CSSProperties } from 'react';
import clsx from 'clsx';

interface SliderControlProps {
  id: string;
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (value: number) => void;
}

export function SliderControl({ id, label, value, min = 0, max = 100, step = 1, onChange }: SliderControlProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(Number(event.target.value));
  };

  const normalized = (value - min) / (max - min || 1);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-slate-200/80">
        <label htmlFor={id}>{label}</label>
        <span className="font-mono text-neon-cyan">{value}</span>
      </div>
      <div className="relative" style={{ '--value': normalized } as CSSProperties}>
        <div className="absolute inset-0 -z-10 rounded-full bg-gradient-to-r from-holo-200/40 via-holo-400/40 to-transparent blur" />
        <input
          id={id}
          type="range"
          min={min}
          max={max}
          value={value}
          step={step}
          onChange={handleChange}
          className={clsx(
            'w-full appearance-none rounded-full bg-slate-800/80 p-[3px] shadow-inner',
            'accent-neon-cyan'
          )}
        />
        <div className="pointer-events-none absolute left-[calc(var(--value,0)*100%)] top-1/2 h-3 w-3 -translate-y-1/2 -translate-x-1/2 rounded-full bg-neon-cyan shadow-holo" />
      </div>
    </div>
  );
}
