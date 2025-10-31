'use client';

import { useMemo } from 'react';
import { ControlPanel } from '@/components/dashboard/ControlPanel';
import { HolographicTimeline } from '@/components/timeline/HolographicTimeline';
import { HoloCard } from '@/components/ui/HoloCard';
import { KPIPanel } from '@/components/dashboard/KPIPanel';
import { ScenarioComparison } from '@/components/dashboard/ScenarioComparison';
import { useRosteringEngine } from '@/lib/rosterClient';
import type { RosterResult } from '@/types/roster';

const base = new Date();
base.setMinutes(0, 0, 0);

const timeAt = (hour: number) => {
  const clone = new Date(base);
  clone.setHours(hour, 0, 0, 0);
  return clone.toISOString();
};

const mockResult: RosterResult = {
  feasible: true,
  objectiveValue: 1280,
  assignments: [
    {
      slotId: 'A1',
      guardId: 'Echo-7',
      start: timeAt(6),
      end: timeAt(10),
    },
    {
      slotId: 'B2',
      guardId: 'Echo-7',
      start: timeAt(12),
      end: timeAt(16),
    },
    {
      slotId: 'C3',
      guardId: 'Atlas-4',
      start: timeAt(8),
      end: timeAt(14),
    },
    {
      slotId: 'D4',
      guardId: 'Nova-2',
      start: timeAt(14),
      end: timeAt(20),
    },
  ],
  kpis: [
    { label: 'Coverage Index', value: '97%', delta: '+2%', status: 'positive' },
    { label: 'Fairness Alignment', value: '0.92', delta: '+0.04', status: 'positive' },
    { label: 'Fatigue Risk', value: 'Low', delta: '-8%', status: 'neutral' },
  ],
  comparisons: [
    { name: 'Alpha Strike', objectiveValue: 1280, coverageScore: 0.97, fairnessScore: 0.92, feasibility: true },
    { name: 'Beta Shield', objectiveValue: 1365, coverageScore: 0.94, fairnessScore: 0.88, feasibility: true },
    { name: 'Gamma Drift', objectiveValue: 1432, coverageScore: 0.89, fairnessScore: 0.76, feasibility: false },
  ],
};

export default function CommandCenterPage() {
  const { result, status, connected, lastUpdated, sendCriteria } = useRosteringEngine(mockResult);
  const activeResult = result ?? mockResult;

  const assignmentSummary = useMemo(() => {
    const guards = Array.from(new Set(activeResult.assignments.map((assignment) => assignment.guardId)));
    return `${guards.length} active agents | ${activeResult.assignments.length} assignments`;
  }, [activeResult.assignments]);

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-12">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-mono uppercase tracking-[0.5em] text-neon-cyan">PSG // Jarvis Command</p>
        <h1 className="font-display text-4xl uppercase tracking-[0.4em] text-white">Rostering Intelligence Deck</h1>
        <p className="text-sm text-slate-300/80">
          {status} {connected ? '• Live Link Engaged' : '• Standby Mode'}
        </p>
        {lastUpdated && <p className="text-xs text-slate-400/70">Last sync: {new Date(lastUpdated).toLocaleTimeString()}</p>}
      </header>

      <section className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
        <ControlPanel onSubmit={sendCriteria} />
        <div className="space-y-6">
          <HoloCard title="Tactical Overview" subtitle={assignmentSummary}>
            <HolographicTimeline assignments={activeResult.assignments} />
          </HoloCard>
          <HoloCard title="Mission KPIs" subtitle="Operational telemetry snapshot" glow="cyan">
            <KPIPanel kpis={activeResult.kpis} />
          </HoloCard>
        </div>
      </section>

      <HoloCard title="Scenario Intelligence" subtitle="Compare mission alternatives" glow="blue">
        <ScenarioComparison scenarios={activeResult.comparisons} activeScenario={activeResult.comparisons[0]?.name} />
      </HoloCard>
    </main>
  );
}
