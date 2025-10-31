'use client';

import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { Assignment } from '@/types/roster';
import { getRoleBadgeClass, getRoleGradient } from '@/lib/roleStyles';

interface HolographicTimelineProps {
  assignments: Assignment[];
  visibleGuardIds?: string[];
}

const timelineVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

function formatHour(date: string) {
  const d = new Date(date);
  return `${d.getHours().toString().padStart(2, '0')}:00`;
}

function computeDuration(start: string, end: string) {
  return Math.max(1, (new Date(end).getTime() - new Date(start).getTime()) / 3_600_000);
}

function startOffset(start: string) {
  return new Date(start).getHours();
}

export function HolographicTimeline({ assignments, visibleGuardIds }: HolographicTimelineProps) {
  const guards = Array.from(new Set(assignments.map((assignment) => assignment.guardId)));

  return (
    <div className="space-y-4">
      {guards.map((guardId, index) => {
        if (visibleGuardIds && !visibleGuardIds.includes(guardId)) return null;
        const guardAssignments = assignments.filter((assignment) => assignment.guardId === guardId);
        return (
          <motion.div
            key={guardId}
            variants={timelineVariants}
            initial="hidden"
            animate="visible"
            transition={{ duration: 0.4, delay: index * 0.1 }}
            className="rounded-2xl border border-holo-400/30 bg-slate-900/40 p-4 shadow-holo"
          >
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 rounded-full bg-neon-cyan shadow-holo" />
                <h3 className="font-display text-sm uppercase tracking-[0.25em] text-slate-100">Guard {guardId}</h3>
              </div>
              <span className="text-xs text-slate-300/70">{guardAssignments.length} missions</span>
            </div>
            <div className="space-y-2">
              {guardAssignments.map((assignment) => (
                <motion.div
                  key={`${assignment.slotId}-${assignment.start}`}
                  initial={{ width: 0, opacity: 0 }}
                  animate={{
                    width: `${(computeDuration(assignment.start, assignment.end) / 24) * 100}%`,
                    opacity: 1,
                    marginLeft: `${(startOffset(assignment.start) / 24) * 100}%`,
                  }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                  className={clsx(
                    'relative flex items-center rounded-xl border border-cyan-300/30 bg-gradient-to-r p-3 text-sm shadow-holo',
                    getRoleGradient(assignment.role)
                  )}
                >
                  <div className="flex-1">
                    <p className="font-mono text-xs text-slate-100/80">Slot {assignment.slotId}</p>
                    <p className="text-xs text-white/90">
                      {formatHour(assignment.start)} – {formatHour(assignment.end)}
                    </p>
                  </div>
                  <span
                    className={clsx(
                      'rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.2em] shadow-holo',
                      getRoleBadgeClass(assignment.role)
                    )}
                  >
                    {assignment.role ?? 'General'}
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
