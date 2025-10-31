'use client';

import type { ScenarioComparison as Scenario } from '@/types/roster';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface ScenarioComparisonProps {
  scenarios: Scenario[];
  activeScenario?: string;
}

export function ScenarioComparison({ scenarios, activeScenario }: ScenarioComparisonProps) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {scenarios.map((scenario, index) => (
        <motion.article
          key={scenario.name}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className={clsx(
            'rounded-3xl border border-holo-400/40 bg-slate-900/60 p-5 shadow-holo backdrop-blur-lg transition-all',
            activeScenario === scenario.name ? 'border-neon-cyan/60 shadow-holo' : 'opacity-90'
          )}
        >
          <header className="mb-3 flex items-center justify-between">
            <h3 className="font-display text-sm uppercase tracking-[0.25em] text-slate-100">{scenario.name}</h3>
            <span
              className={clsx(
                'rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.2em]',
                scenario.feasibility
                  ? 'border-neon-cyan/60 text-neon-cyan'
                  : 'border-red-400/50 text-red-300'
              )}
            >
              {scenario.feasibility ? 'Feasible' : 'Risk'}
            </span>
          </header>
          <dl className="space-y-2 text-xs text-slate-300/80">
            <div className="flex justify-between">
              <dt>Objective</dt>
              <dd className="font-mono text-neon-cyan">{scenario.objectiveValue?.toFixed(0) ?? '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Coverage</dt>
              <dd className="font-mono text-neon-indigo">{Math.round(scenario.coverageScore * 100)}%</dd>
            </div>
            <div className="flex justify-between">
              <dt>Fairness</dt>
              <dd className="font-mono text-neon-blue">{Math.round(scenario.fairnessScore * 100)}%</dd>
            </div>
          </dl>
        </motion.article>
      ))}
    </div>
  );
}
