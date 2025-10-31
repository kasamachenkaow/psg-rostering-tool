"""Core rostering engine with CP-SAT integration.

This module defines the canonical data models used by the rostering
engine as well as a convenience wrapper around the CP-SAT solver from
OR-Tools.  The solver formulation focuses on the most common shift
planning requirements (coverage, rest, and fairness) and exposes a
configuration object that lets callers tune which constraints are treated
as hard requirements and which are allowed to be violated with a
penalty.

The engine can be used in two different modes:
    * Direct roster generation with a fixed guard pool.
    * Iterative guard-pool sizing where the solver is executed multiple
      times until a feasible roster is found, yielding the minimum pool
      size that satisfies the specified constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:  # pragma: no cover - import guard to keep module importable without ortools
    from ortools.sat.python import cp_model
except ImportError as exc:  # pragma: no cover - surface a clear runtime error when needed
    cp_model = None  # type: ignore[assignment]
    _ORTOOLS_IMPORT_ERROR = exc
else:
    _ORTOOLS_IMPORT_ERROR = None


@dataclass(frozen=True)
class GuardProfile:
    """Describes an individual guard that can be assigned to shifts."""

    guard_id: str
    name: str
    skills: Sequence[str] = field(default_factory=tuple)
    roles: Sequence[str] = field(default_factory=tuple)
    max_hours_per_week: Optional[float] = None
    priority: int = 0


@dataclass(frozen=True)
class DemandSlot:
    """Represents a demand requirement for a contiguous block of time."""

    slot_id: str
    start: datetime
    end: datetime
    required_guards: int = 1
    required_skill: Optional[str] = None
    required_roles: Dict[str, int] = field(default_factory=dict)

    def duration_hours(self) -> float:
        """Return the duration of the slot in hours."""

        delta = self.end - self.start
        return delta.total_seconds() / 3600.0

    def day_index(self) -> int:
        """Return a comparable day index for consecutive-day calculations."""

        return self.start.date().toordinal()


@dataclass
class HardConstraintSpec:
    """Constraint toggles that are enforced as hard requirements."""

    enforce_coverage: bool = True
    enforce_skill_requirements: bool = True
    enforce_role_coverage: bool = False
    max_consecutive_days: Optional[int] = None
    min_break_hours: Optional[float] = None
    rest_window_hours: Optional[float] = None


@dataclass
class SoftConstraintWeights:
    """Weights (penalties) applied when soft constraints are violated."""

    coverage_shortfall: int = 1_000
    min_break_violation: int = 250
    rest_window_violation: int = 250
    consecutive_day_violation: int = 400
    fairness_penalty: int = 10


@dataclass
class RosterConstraintConfig:
    """Aggregates constraint configuration for the rostering engine."""

    hard: HardConstraintSpec = field(default_factory=HardConstraintSpec)
    soft: SoftConstraintWeights = field(default_factory=SoftConstraintWeights)
    fairness_target_hours: Optional[float] = None


@dataclass
class RosterResult:
    """Container for the outcome of a rostering solve attempt."""

    feasible: bool
    assignments: Dict[str, List[str]]
    objective_value: Optional[float]
    violation_summaries: Dict[str, Dict[str, float]]
    coverage: Dict[str, Dict[str, Any]]
    status: str
    solver_statistics: Optional[str] = None
    assignment_roles: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)


@dataclass
class StaffingResult:
    """Result from the iterative guard pool sizing search."""

    minimum_guards: Optional[int]
    roster: Optional[RosterResult]
    attempts: Dict[int, RosterResult]


class RosterEngine:
    """High-level façade for CP-SAT based rostering."""

    def __init__(self, constraint_config: Optional[RosterConstraintConfig] = None) -> None:
        if cp_model is None:  # pragma: no cover - raised only when ortools missing
            raise ImportError(
                "OR-Tools is required to use the rostering engine"
            ) from _ORTOOLS_IMPORT_ERROR
        self.constraint_config = constraint_config or RosterConstraintConfig()

    def solve(
        self,
        guards: Sequence[GuardProfile],
        demand_slots: Sequence[DemandSlot],
        time_limit_seconds: Optional[float] = None,
    ) -> RosterResult:
        """Solve for guard assignments given a fixed set of guards and demand."""

        model = cp_model.CpModel()
        assignments: Dict[Tuple[int, int], cp_model.IntVar] = {}
        penalty_terms: List[Tuple[int, cp_model.IntVar, str]] = []
        coverage_stats: Dict[str, Dict[str, Any]] = {}
        guard_role_sets = [
            set(getattr(guard, "roles", ())) | set(guard.skills)
            for guard in guards
        ]

        for g_idx, guard in enumerate(guards):
            for s_idx, slot in enumerate(demand_slots):
                variable = model.NewBoolVar(f"assign_g{g_idx}_s{s_idx}")
                assignments[(g_idx, s_idx)] = variable
                if (
                    self.constraint_config.hard.enforce_skill_requirements
                    and slot.required_skill
                    and slot.required_skill not in set(guard.skills)
                ):
                    model.Add(variable == 0)

        # Coverage constraints
        for s_idx, slot in enumerate(demand_slots):
            assigned = [assignments[(g_idx, s_idx)] for g_idx in range(len(guards))]
            role_requirements = slot.required_roles or {}
            total_role_required = sum(role_requirements.values())
            required_total = max(slot.required_guards, total_role_required)
            coverage_stats[slot.slot_id] = {
                "required": required_total,
            }
            if role_requirements:
                role_stats: Dict[str, Dict[str, int]] = {}
                for role, count in role_requirements.items():
                    role_stats[role] = {"required": count, "assigned": 0}
                    if self.constraint_config.hard.enforce_role_coverage:
                        eligible = [
                            assignments[(g_idx, s_idx)]
                            for g_idx, role_set in enumerate(guard_role_sets)
                            if role in role_set
                        ]
                        if eligible:
                            model.Add(sum(eligible) >= count)
                        else:
                            model.Add(sum([]) >= count)
                coverage_stats[slot.slot_id]["roles"] = role_stats
            if self.constraint_config.hard.enforce_coverage:
                model.Add(sum(assigned) >= required_total)
            else:
                slack = model.NewIntVar(0, required_total, f"coverage_slack_{s_idx}")
                model.Add(sum(assigned) + slack >= required_total)
                penalty_terms.append(
                    (
                        self.constraint_config.soft.coverage_shortfall,
                        slack,
                        f"coverage_shortfall::{slot.slot_id}",
                    )
                )

        # Guard daily presence and max consecutive days.
        if self.constraint_config.hard.max_consecutive_days is not None or self.constraint_config.soft.consecutive_day_violation:
            slots_by_day: Dict[int, List[int]] = {}
            for idx, slot in enumerate(demand_slots):
                slots_by_day.setdefault(slot.day_index(), []).append(idx)
            sorted_days = sorted(slots_by_day)
            day_presence: Dict[Tuple[int, int], cp_model.IntVar] = {}
            for g_idx in range(len(guards)):
                for day_idx, day in enumerate(sorted_days):
                    presence = model.NewBoolVar(f"presence_g{g_idx}_d{day_idx}")
                    day_slots = slots_by_day[day]
                    slot_vars = [assignments[(g_idx, s_idx)] for s_idx in day_slots]
                    model.Add(sum(slot_vars) >= 1).OnlyEnforceIf(presence)
                    model.Add(sum(slot_vars) == 0).OnlyEnforceIf(presence.Not())
                    day_presence[(g_idx, day_idx)] = presence

                if not sorted_days:
                    continue
                max_consec = self.constraint_config.hard.max_consecutive_days
                if max_consec is not None:
                    for start in range(0, len(sorted_days) - max_consec):
                        window_presence = [
                            day_presence[(g_idx, day_idx)]
                            for day_idx in range(start, start + max_consec + 1)
                        ]
                        model.Add(sum(window_presence) <= max_consec)
                elif self.constraint_config.soft.consecutive_day_violation:
                    max_consec = 0
                    for start in range(0, len(sorted_days)):
                        window_presence = [
                            day_presence[(g_idx, day_idx)]
                            for day_idx in range(start, len(sorted_days))
                        ]
                        window_sum = model.NewIntVar(
                            0,
                            len(window_presence),
                            f"consec_sum_g{g_idx}_w{start}",
                        )
                        model.Add(window_sum == sum(window_presence))
                        slack = model.NewIntVar(
                            0,
                            len(window_presence),
                            f"consec_slack_g{g_idx}_w{start}",
                        )
                        model.Add(window_sum <= max_consec + slack)
                        penalty_terms.append(
                            (
                                self.constraint_config.soft.consecutive_day_violation,
                                slack,
                                f"consecutive_day_violation::guard={guards[g_idx].guard_id}::window={start}",
                            )
                        )

        # Rest windows and minimum breaks between shifts for each guard.
        min_break = self.constraint_config.hard.min_break_hours
        rest_window = self.constraint_config.hard.rest_window_hours
        soft_break_weight = self.constraint_config.soft.min_break_violation
        soft_rest_weight = self.constraint_config.soft.rest_window_violation
        for g_idx in range(len(guards)):
            for i, first in enumerate(demand_slots):
                for j, second in enumerate(demand_slots):
                    if j <= i:
                        continue
                    gap_after_first = (second.start - first.end).total_seconds() / 3600.0
                    gap_before_first = (first.start - second.end).total_seconds() / 3600.0
                    assign_first = assignments[(g_idx, i)]
                    assign_second = assignments[(g_idx, j)]
                    if min_break is not None and -min_break < gap_after_first < min_break:
                        if self.constraint_config.hard.min_break_hours is not None:
                            model.Add(assign_first + assign_second <= 1)
                        elif soft_break_weight:
                            slack = model.NewBoolVar(
                                f"break_slack_g{g_idx}_{i}_{j}"
                            )
                            model.Add(assign_first + assign_second <= 1 + slack)
                            penalty_terms.append(
                                (
                                    soft_break_weight,
                                    slack,
                                    f"min_break_violation::guard={guards[g_idx].guard_id}::{first.slot_id}->{second.slot_id}",
                                )
                            )
                    if rest_window is not None and 0 <= gap_after_first < rest_window:
                        if self.constraint_config.hard.rest_window_hours is not None:
                            model.Add(assign_first + assign_second <= 1)
                        elif soft_rest_weight:
                            slack = model.NewBoolVar(
                                f"rest_slack_g{g_idx}_{i}_{j}"
                            )
                            model.Add(assign_first + assign_second <= 1 + slack)
                            penalty_terms.append(
                                (
                                    soft_rest_weight,
                                    slack,
                                    f"rest_window_violation::guard={guards[g_idx].guard_id}::{first.slot_id}->{second.slot_id}",
                                )
                            )
                    # also check symmetric direction
                    if rest_window is not None and 0 <= gap_before_first < rest_window:
                        if self.constraint_config.hard.rest_window_hours is not None:
                            model.Add(assign_first + assign_second <= 1)
                        elif soft_rest_weight:
                            slack = model.NewBoolVar(
                                f"rest_slack_g{g_idx}_{j}_{i}"
                            )
                            model.Add(assign_first + assign_second <= 1 + slack)
                            penalty_terms.append(
                                (
                                    soft_rest_weight,
                                    slack,
                                    f"rest_window_violation::guard={guards[g_idx].guard_id}::{second.slot_id}->{first.slot_id}",
                                )
                            )

        # Guard load tracking for fairness calculations.
        guard_totals: Dict[int, cp_model.IntVar] = {}
        for g_idx in range(len(guards)):
            total_assignments = model.NewIntVar(0, len(demand_slots), f"total_assign_g{g_idx}")
            guard_totals[g_idx] = total_assignments
            model.Add(
                total_assignments
                == sum(assignments[(g_idx, s_idx)] for s_idx in range(len(demand_slots)))
            )

        fairness_weight = self.constraint_config.soft.fairness_penalty
        if fairness_weight and guard_totals:
            max_total = model.NewIntVar(0, len(demand_slots), "max_assignments")
            min_total = model.NewIntVar(0, len(demand_slots), "min_assignments")
            for total in guard_totals.values():
                model.Add(total <= max_total)
                model.Add(total >= min_total)
            fairness_span = model.NewIntVar(0, len(demand_slots), "fairness_span")
            model.Add(fairness_span == max_total - min_total)
            penalty_terms.append(
                (
                    fairness_weight,
                    fairness_span,
                    "fairness_span",
                )
            )

            target_hours = self.constraint_config.fairness_target_hours
            if target_hours is not None and demand_slots:
                average_slot_hours = (
                    sum(slot.duration_hours() for slot in demand_slots) / len(demand_slots)
                )
                if average_slot_hours <= 0:
                    average_slot_hours = 1.0
                expected_assignments = max(
                    0, int(round(target_hours / average_slot_hours))
                )
                for g_idx, guard in enumerate(guards):
                    deviation = model.NewIntVar(0, len(demand_slots), f"deviation_g{g_idx}")
                    model.Add(deviation >= guard_totals[g_idx] - expected_assignments)
                    model.Add(deviation >= expected_assignments - guard_totals[g_idx])
                    penalty_terms.append(
                        (
                            fairness_weight,
                            deviation,
                            f"fairness_target_deviation::guard={guard.guard_id}",
                        )
                    )

        # Objective function accumulates all soft penalties.
        if penalty_terms:
            objective_terms = [
                weight * term for weight, term, _ in penalty_terms
            ]
            model.Minimize(sum(objective_terms))

        solver = cp_model.CpSolver()
        if time_limit_seconds:
            solver.parameters.max_time_in_seconds = time_limit_seconds

        status = solver.Solve(model)
        status_name = solver.StatusName(status)
        feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        assignments_output: Dict[str, List[str]] = {guard.guard_id: [] for guard in guards}
        assignment_roles: Dict[str, Dict[str, Optional[str]]] = {
            guard.guard_id: {} for guard in guards
        }

        if feasible:
            for slot_stats in coverage_stats.values():
                roles_map = slot_stats.get("roles")
                if isinstance(roles_map, dict):
                    for role_info in roles_map.values():
                        role_info["assigned"] = 0

            assigned_by_slot: Dict[int, List[int]] = {}
            for (g_idx, s_idx), var in assignments.items():
                if solver.BooleanValue(var):
                    guard_id = guards[g_idx].guard_id
                    slot_id = demand_slots[s_idx].slot_id
                    assignments_output[guard_id].append(slot_id)
                    assignment_roles[guard_id][slot_id] = None
                    assigned_by_slot.setdefault(s_idx, []).append(g_idx)

            for s_idx, slot in enumerate(demand_slots):
                guard_indices = assigned_by_slot.get(s_idx, [])
                slot_stats = coverage_stats[slot.slot_id]
                slot_stats["assigned"] = len(guard_indices)
                if not guard_indices:
                    continue

                remaining_roles = dict(slot.required_roles)
                for g_idx in guard_indices:
                    guard_id = guards[g_idx].guard_id
                    slot_id = slot.slot_id
                    assigned_role: Optional[str] = None
                    guard_roles = guard_role_sets[g_idx]
                    for role, remaining in remaining_roles.items():
                        if remaining > 0 and role in guard_roles:
                            assigned_role = role
                            remaining_roles[role] -= 1
                            break
                    assignment_roles[guard_id][slot_id] = assigned_role
                    roles_map = slot_stats.get("roles")
                    if (
                        assigned_role
                        and isinstance(roles_map, dict)
                        and assigned_role in roles_map
                    ):
                        roles_map[assigned_role]["assigned"] += 1
        else:
            for slot in demand_slots:
                slot_stats = coverage_stats[slot.slot_id]
                slot_stats.setdefault("assigned", 0)
                roles_map = slot_stats.get("roles")
                if isinstance(roles_map, dict):
                    for role_info in roles_map.values():
                        role_info.setdefault("assigned", 0)

        violation_summaries: Dict[str, Dict[str, float]] = {}
        if penalty_terms and feasible:
            for weight, term, name in penalty_terms:
                value = solver.Value(term)
                if value:
                    violation_summaries[name] = {
                        "value": float(value),
                        "penalty": float(weight * value),
                    }
        elif not feasible:
            violation_summaries["status"] = {"value": float(status), "penalty": 0.0}

        objective_value: Optional[float]
        if feasible and penalty_terms:
            objective_value = solver.ObjectiveValue()
        elif feasible:
            objective_value = 0.0
        else:
            objective_value = None

        solver_stats = solver.ResponseStats() if status != cp_model.UNKNOWN else None

        return RosterResult(
            feasible=feasible,
            assignments=assignments_output,
            objective_value=objective_value,
            violation_summaries=violation_summaries,
            coverage=coverage_stats,
            status=status_name,
            solver_statistics=solver_stats,
            assignment_roles=assignment_roles,
        )

    def find_minimum_staffing(
        self,
        guards: Sequence[GuardProfile],
        demand_slots: Sequence[DemandSlot],
        minimum: int = 1,
        maximum: Optional[int] = None,
        time_limit_seconds: Optional[float] = None,
    ) -> StaffingResult:
        """Iteratively increase the guard pool until a feasible roster is found."""

        ordered_guards = sorted(guards, key=lambda g: (g.priority, g.guard_id))
        max_size = maximum or len(ordered_guards)
        attempts: Dict[int, RosterResult] = {}
        feasible_result: Optional[RosterResult] = None
        feasible_size: Optional[int] = None

        for size in range(max(minimum, 1), max_size + 1):
            subset = ordered_guards[:size]
            result = self.solve(subset, demand_slots, time_limit_seconds=time_limit_seconds)
            attempts[size] = result
            if result.feasible:
                feasible_result = result
                feasible_size = size
                break

        return StaffingResult(
            minimum_guards=feasible_size,
            roster=feasible_result,
            attempts=attempts,
        )
