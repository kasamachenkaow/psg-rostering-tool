export type DemandSlot = {
  slotId: string;
  start: string;
  end: string;
  requiredGuards: number;
  requiredSkill?: string | null;
};

export type GuardProfile = {
  guardId: string;
  name: string;
  skills: string[];
  maxHoursPerWeek?: number | null;
  priority?: number;
};

export type Assignment = {
  slotId: string;
  guardId: string;
  start: string;
  end: string;
};

export type RosterKPI = {
  label: string;
  value: string;
  delta?: string;
  status?: 'positive' | 'negative' | 'neutral';
};

export type ScenarioComparison = {
  name: string;
  objectiveValue?: number | null;
  coverageScore: number;
  fairnessScore: number;
  feasibility: boolean;
};

export type RosterResult = {
  feasible: boolean;
  objectiveValue: number | null;
  assignments: Assignment[];
  kpis: RosterKPI[];
  comparisons: ScenarioComparison[];
};

export type EngineCriteria = {
  sliders: Record<string, number>;
  toggles: Record<string, boolean>;
  scenarioName: string;
};

export type EngineMessage = {
  type: 'criteria' | 'result' | 'error' | 'status';
  payload: unknown;
};
