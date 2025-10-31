'use client';

import type { RosterKPI } from '@/types/roster';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface KPIPanelProps {
  kpis: RosterKPI[];
}

const statusStyles: Record<NonNullable<RosterKPI['status']>, string> = {
  positive: 'text-neon-cyan',
  negative: 'text-red-400',
  neutral: 'text-slate-200',
};

export function KPIPanel({ kpis }: KPIPanelProps) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {kpis.map((kpi, index) => (
        <motion.div
          key={kpi.label}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.1 }}
          className="rounded-3xl border border-holo-400/40 bg-slate-900/50 p-4 shadow-holo"
        >
          <p className="text-xs uppercase tracking-[0.35em] text-slate-300/70">{kpi.label}</p>
          <p className={clsx('mt-2 text-2xl font-semibold', kpi.status ? statusStyles[kpi.status] : 'text-white')}>
            {kpi.value}
          </p>
          {kpi.delta && (
            <p className="mt-1 text-xs text-slate-400/80">Δ {kpi.delta}</p>
          )}
        </motion.div>
      ))}
    </div>
  );
}
