'use client';

import { useEffect, useState } from 'react';
import { SliderControl } from '@/components/ui/SliderControl';
import { ToggleSwitch } from '@/components/ui/ToggleSwitch';
import { HoloCard } from '@/components/ui/HoloCard';
import type { EngineCriteria } from '@/types/roster';

interface ControlPanelProps {
  onSubmit: (criteria: EngineCriteria) => void;
}

const sliderDefaults = {
  coverage: 80,
  fairness: 50,
  resilience: 60,
};

const toggleDefaults = {
  allowOvertime: false,
  prioritizeRest: true,
  dynamicSizing: true,
};

export function ControlPanel({ onSubmit }: ControlPanelProps) {
  const [sliders, setSliders] = useState(sliderDefaults);
  const [toggles, setToggles] = useState(toggleDefaults);
  const [scenarioName, setScenarioName] = useState('Alpha Strike');

  useEffect(() => {
    onSubmit({ sliders, toggles, scenarioName });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSliderChange = (key: keyof typeof sliderDefaults) => (value: number) => {
    const next = { ...sliders, [key]: value };
    setSliders(next);
    onSubmit({ sliders: next, toggles, scenarioName });
  };

  const handleToggleChange = (key: keyof typeof toggleDefaults) => (value: boolean) => {
    const next = { ...toggles, [key]: value };
    setToggles(next);
    onSubmit({ sliders, toggles: next, scenarioName });
  };

  return (
    <div className="space-y-6">
      <HoloCard title="Mission Parameters" subtitle="Real-time constraint tuning" glow="indigo">
        <div className="grid gap-5">
          <div className="grid gap-4">
            <SliderControl
              id="coverage"
              label="Coverage Assurance"
              value={sliders.coverage}
              min={60}
              max={100}
              onChange={handleSliderChange('coverage')}
            />
            <SliderControl
              id="fairness"
              label="Fairness Bias"
              value={sliders.fairness}
              min={0}
              max={100}
              onChange={handleSliderChange('fairness')}
            />
            <SliderControl
              id="resilience"
              label="Resilience Reserve"
              value={sliders.resilience}
              min={0}
              max={100}
              onChange={handleSliderChange('resilience')}
            />
          </div>
          <div className="grid gap-3">
            <ToggleSwitch
              id="allow-overtime"
              label="Overtime Authorization"
              description="Allow calculated overtime spillover for critical missions"
              value={toggles.allowOvertime}
              onChange={handleToggleChange('allowOvertime')}
            />
            <ToggleSwitch
              id="prioritize-rest"
              label="Rest Protocol"
              description="Prioritize recovery windows over coverage flexibility"
              value={toggles.prioritizeRest}
              onChange={handleToggleChange('prioritizeRest')}
            />
            <ToggleSwitch
              id="dynamic-sizing"
              label="Dynamic Taskforce"
              description="Iteratively adjust guard pool for feasibility"
              value={toggles.dynamicSizing}
              onChange={handleToggleChange('dynamicSizing')}
            />
          </div>
        </div>
      </HoloCard>
      <HoloCard title="Scenario Codename" subtitle="Track and compare mission plans" glow="blue">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={scenarioName}
            onChange={(event) => {
              const name = event.target.value;
              setScenarioName(name);
              onSubmit({ sliders, toggles, scenarioName: name });
            }}
            className="flex-1 rounded-2xl border border-holo-400/40 bg-slate-900/60 px-4 py-3 font-display text-sm uppercase tracking-[0.3em] text-neon-cyan shadow-inner focus:border-neon-cyan/70 focus:outline-none"
            placeholder="Scenario name"
          />
          <button
            type="button"
            onClick={() => onSubmit({ sliders, toggles, scenarioName })}
            className="rounded-2xl border border-neon-cyan/60 bg-gradient-to-r from-neon-cyan/50 to-neon-blue/40 px-4 py-3 font-display text-xs uppercase tracking-[0.35em] text-white shadow-holo transition hover:from-neon-cyan/70 hover:to-neon-blue/60"
          >
            Sync
          </button>
        </div>
      </HoloCard>
    </div>
  );
}
