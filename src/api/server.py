"""FastAPI service exposing the rostering engine via REST and WebSocket."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from src.rostering.engine import (
    DemandSlot,
    GuardProfile,
    HardConstraintSpec,
    RosterConstraintConfig,
    RosterEngine,
    RosterResult,
    SoftConstraintWeights,
)


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class EngineCriteriaModel(CamelModel):
    sliders: Dict[str, float]
    toggles: Dict[str, bool]
    scenario_name: str = Field(alias="scenarioName")


class AssignmentModel(CamelModel):
    slot_id: str
    guard_id: str
    start: datetime
    end: datetime
    role: Optional[str] = None


class KPIModel(CamelModel):
    label: str
    value: str
    delta: Optional[str] = None
    status: Optional[str] = None


class ScenarioComparisonModel(CamelModel):
    name: str
    objective_value: Optional[float] = None
    coverage_score: float
    fairness_score: float
    feasibility: bool


class RoleCoverageModel(CamelModel):
    role: str
    required: int
    assigned: int


class RosterResponseModel(CamelModel):
    feasible: bool
    objective_value: Optional[float]
    assignments: List[AssignmentModel]
    kpis: List[KPIModel]
    comparisons: List[ScenarioComparisonModel]
    mode: str
    role_coverage: List[RoleCoverageModel]
    alerts: List[str]


class RosteringService:
    """Coordinates calls into the rostering engine and crafts dashboard payloads."""

    def __init__(self) -> None:
        self._engine: Optional[RosterEngine]
        try:
            self._engine = RosterEngine()
        except ImportError:
            self._engine = None

        base = datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0)
        self._guards = [
            GuardProfile(
                guard_id="Echo-7",
                name="Echo 7",
                skills=("standard", "emergency"),
                roles=("Leader", "Responder"),
                priority=1,
            ),
            GuardProfile(
                guard_id="Atlas-4",
                name="Atlas 4",
                skills=("standard", "technical"),
                roles=("Technician", "Supervisor"),
                priority=2,
            ),
            GuardProfile(
                guard_id="Nova-2",
                name="Nova 2",
                skills=("standard",),
                roles=("Supervisor",),
                priority=3,
            ),
            GuardProfile(
                guard_id="Vanguard-9",
                name="Vanguard 9",
                skills=("technical",),
                roles=("Technician",),
                priority=4,
            ),
        ]
        self._slots = [
            DemandSlot(
                slot_id="A1",
                start=base,
                end=base + timedelta(hours=4),
                required_guards=2,
                required_roles={"Leader": 1, "Technician": 1},
            ),
            DemandSlot(
                slot_id="B2",
                start=base + timedelta(hours=2),
                end=base + timedelta(hours=8),
                required_guards=1,
                required_roles={"Supervisor": 1},
            ),
            DemandSlot(
                slot_id="C3",
                start=base + timedelta(hours=8),
                end=base + timedelta(hours=12),
                required_guards=1,
                required_roles={"Leader": 1},
            ),
            DemandSlot(
                slot_id="D4",
                start=base + timedelta(hours=12),
                end=base + timedelta(hours=18),
                required_guards=1,
                required_roles={"Technician": 1},
            ),
        ]

    def generate_schedule(self, criteria: EngineCriteriaModel) -> RosterResponseModel:
        result: Optional[RosterResult] = None
        if self._engine:
            result = self._solve_with_engine(criteria)

        if result is None:
            result = self._mock_schedule(criteria)
        return self._build_response(criteria, result)

    def _solve_with_engine(self, criteria: EngineCriteriaModel) -> Optional[RosterResult]:
        sliders = criteria.sliders
        toggles = criteria.toggles

        role_aware = toggles.get("roleAwareSimulation", False)

        hard = HardConstraintSpec(
            enforce_coverage=True,
            enforce_skill_requirements=True,
            enforce_role_coverage=role_aware,
            min_break_hours=12.0 if toggles.get("prioritizeRest", True) else 8.0,
            rest_window_hours=24.0 if toggles.get("prioritizeRest", True) else None,
        )
        soft = SoftConstraintWeights(
            coverage_shortfall=max(100, int((100 - sliders.get("coverage", 80)) * 12 + 500)),
            fairness_penalty=max(5, int((100 - sliders.get("fairness", 50)) * 2 + 10)),
            rest_window_violation=max(100, int(sliders.get("resilience", 60) * 3)),
        )
        config = RosterConstraintConfig(hard=hard, soft=soft)
        try:
            engine = RosterEngine(config)
            result = engine.solve(self._guards, self._slots)
        except Exception:
            return None
        return result

    def _mock_schedule(self, criteria: EngineCriteriaModel) -> RosterResult:
        coverage = criteria.sliders.get("coverage", 80)
        fairness = criteria.sliders.get("fairness", 50)
        assignments_map: Dict[str, List[str]] = {
            "Echo-7": ["A1", "C3"],
            "Atlas-4": ["A1"],
            "Nova-2": ["B2"],
            "Vanguard-9": ["D4"],
        }
        assignment_roles = {
            "Echo-7": {"A1": "Leader", "C3": "Leader"},
            "Atlas-4": {"A1": "Technician"},
            "Nova-2": {"B2": "Supervisor"},
            "Vanguard-9": {"D4": "Technician"},
        }
        coverage_snapshot: Dict[str, Dict[str, object]] = {
            "A1": {
                "required": 2,
                "assigned": 2,
                "roles": {
                    "Leader": {"required": 1, "assigned": 1},
                    "Technician": {"required": 1, "assigned": 1},
                },
            },
            "B2": {
                "required": 1,
                "assigned": 1,
                "roles": {"Supervisor": {"required": 1, "assigned": 1}},
            },
            "C3": {
                "required": 1,
                "assigned": 1,
                "roles": {"Leader": {"required": 1, "assigned": 1}},
            },
            "D4": {
                "required": 1,
                "assigned": 1,
                "roles": {"Technician": {"required": 1, "assigned": 1}},
            },
        }
        feasible = coverage >= 70
        objective = 1200 + (coverage - 80) * 8 + (fairness - 50) * 4
        return RosterResult(
            feasible=feasible,
            assignments=assignments_map,
            objective_value=float(objective),
            violation_summaries={},
            coverage=coverage_snapshot,
            status="mock",
            solver_statistics=None,
            assignment_roles=assignment_roles,
        )

    def _build_response(
        self,
        criteria: EngineCriteriaModel,
        result: RosterResult,
    ) -> RosterResponseModel:
        slot_lookup = {slot.slot_id: slot for slot in self._slots}
        assignments: List[AssignmentModel] = []
        for guard_id, slot_ids in result.assignments.items():
            for slot_id in slot_ids:
                slot = slot_lookup.get(slot_id)
                if not slot:
                    continue
                role = result.assignment_roles.get(guard_id, {}).get(slot_id)
                assignments.append(
                    AssignmentModel(
                        slot_id=slot.slot_id,
                        guard_id=guard_id,
                        start=slot.start,
                        end=slot.end,
                        role=role,
                    )
                )
        assignments.sort(key=lambda assignment: (assignment.guard_id, assignment.start))

        coverage_required = sum(int(stats.get("required", 0)) for stats in result.coverage.values())
        coverage_assigned = sum(int(stats.get("assigned", 0)) for stats in result.coverage.values())
        required_total = coverage_required if coverage_required else len(assignments)
        assigned_total = coverage_assigned if coverage_required else len(assignments)
        coverage_ratio = assigned_total / required_total if required_total else 0.0

        guard_counts = [len(ids) for ids in result.assignments.values() if ids]
        if guard_counts:
            average = sum(guard_counts) / len(guard_counts)
            dispersion = max(abs(count - average) for count in guard_counts)
            fairness_score = max(0.0, 1.0 - dispersion / max(average, 1.0))
        else:
            fairness_score = 1.0

        fatigue_status = "Low" if criteria.toggles.get("prioritizeRest", True) else "Moderate"

        mode = "role-aware" if criteria.toggles.get("roleAwareSimulation", False) else "aggregate"

        role_totals: Dict[str, Dict[str, int]] = {}
        for slot_stats in result.coverage.values():
            roles_map = slot_stats.get("roles")
            if isinstance(roles_map, dict):
                for role_name, values in roles_map.items():
                    summary = role_totals.setdefault(
                        role_name, {"required": 0, "assigned": 0}
                    )
                    summary["required"] += int(values.get("required", 0))
                    summary["assigned"] += int(values.get("assigned", 0))

        role_coverage = [
            RoleCoverageModel(role=role, required=data["required"], assigned=data["assigned"])
            for role, data in sorted(role_totals.items())
        ]

        alerts: List[str] = []
        for summary in role_coverage:
            if summary.assigned < summary.required:
                deficit = summary.required - summary.assigned
                alerts.append(
                    f"{summary.role} understaffed by {deficit}"
                )

        kpis = [
            KPIModel(label="Coverage Index", value=f"{coverage_ratio * 100:.0f}%", delta="+3%", status="positive"),
            KPIModel(label="Fairness Alignment", value=f"{fairness_score:.2f}", delta="+0.02", status="positive"),
            KPIModel(label="Fatigue Risk", value=fatigue_status, delta="-5%", status="neutral"),
        ]

        comparisons = [
            ScenarioComparisonModel(
                name=criteria.scenario_name,
                objective_value=result.objective_value,
                coverage_score=coverage_ratio,
                fairness_score=fairness_score,
                feasibility=result.feasible,
            ),
            ScenarioComparisonModel(
                name="High Resilience",
                objective_value=result.objective_value * 1.05 if result.objective_value else None,
                coverage_score=min(1.0, coverage_ratio * 0.98),
                fairness_score=min(1.0, fairness_score * 1.05),
                feasibility=result.feasible,
            ),
            ScenarioComparisonModel(
                name="Agile Coverage",
                objective_value=result.objective_value * 1.08 if result.objective_value else None,
                coverage_score=min(1.0, coverage_ratio * 1.03),
                fairness_score=max(0.0, fairness_score * 0.92),
                feasibility=coverage_ratio >= 0.85,
            ),
        ]

        return RosterResponseModel(
            feasible=result.feasible,
            objective_value=result.objective_value,
            assignments=assignments,
            kpis=kpis,
            comparisons=comparisons,
            mode=mode,
            role_coverage=role_coverage,
            alerts=alerts,
        )


service = RosteringService()

app = FastAPI(title="PSG Rostering API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/solve")
async def solve(criteria: EngineCriteriaModel) -> Dict[str, object]:
    schedule = await run_in_threadpool(service.generate_schedule, criteria)
    return schedule.model_dump(by_alias=True)


@app.websocket("/ws/roster")
async def roster_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "status", "payload": "Connected to PSG rostering engine"})
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            payload = data.get("payload")
            if message_type != "criteria" or not isinstance(payload, dict):
                await websocket.send_json({"type": "error", "payload": "Unsupported message"})
                continue
            criteria = EngineCriteriaModel.model_validate(payload)
            schedule = await run_in_threadpool(service.generate_schedule, criteria)
            await websocket.send_json({"type": "result", "payload": schedule.model_dump(by_alias=True)})
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover - defensive logging path
        await websocket.send_json({"type": "error", "payload": str(exc)})
        await websocket.close()
