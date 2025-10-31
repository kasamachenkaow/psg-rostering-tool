'use client';

import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { RoleCoverageSummary as RoleCoverageSummaryType } from '@/types/roster';
import { getRoleBadgeClass } from '@/lib/roleStyles';

interface RoleCoverageSummaryProps {
  coverage: RoleCoverageSummaryType[];
  mode: 'aggregate' | 'role-aware';
}

export function RoleCoverageSummary({ coverage, mode }: RoleCoverageSummaryProps) {
  if (!coverage.length) {
    return (
      <p className="rounded-2xl border border-holo-400/30 bg-slate-900/40 p-4 text-xs text-slate-300/80">
        No role requirements configured for the active scenario.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs uppercase tracking-[0.35em] text-slate-300/70">
        {mode === 'role-aware' ? 'Per-role coverage enforced' : 'Aggregate mode – monitor role gaps'}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {coverage.map((item, index) => {
          const fulfillment = item.required ? Math.min(1, item.assigned / item.required) : 1;
          const progressWidth = `${Math.min(100, fulfillment * 100).toFixed(0)}%`;
          const isSatisfied = item.assigned >= item.required;
          return (
            <motion.div
              key={item.role}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08 }}
              className="rounded-2xl border border-holo-400/30 bg-slate-900/50 p-4 shadow-holo"
            >
              <div className="flex items-center justify-between">
                <span className={clsx('rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.3em]', getRoleBadgeClass(item.role))}>
                  {item.role}
                </span>
                <span className={clsx('text-xs font-mono', isSatisfied ? 'text-emerald-300' : 'text-rose-300')}>
                  {item.assigned} / {item.required}
                </span>
              </div>
              <div className="mt-3 h-2 rounded-full bg-slate-800/70">
                <div
                  className={clsx('h-full rounded-full transition-all', isSatisfied ? 'bg-emerald-400/70' : 'bg-rose-400/70')}
                  style={{ width: progressWidth }}
                />
              </div>
              {!isSatisfied && (
                <p className="mt-2 text-[10px] uppercase tracking-[0.25em] text-rose-200">
                  Understaffed by {item.required - item.assigned}
                </p>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
