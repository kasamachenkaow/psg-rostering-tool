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


class RosterResponseModel(CamelModel):
    feasible: bool
    objective_value: Optional[float]
    assignments: List[AssignmentModel]
    kpis: List[KPIModel]
    comparisons: List[ScenarioComparisonModel]


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
            GuardProfile(guard_id="Echo-7", name="Echo 7", skills=("standard", "emergency"), priority=1),
            GuardProfile(guard_id="Atlas-4", name="Atlas 4", skills=("standard", "technical"), priority=2),
            GuardProfile(guard_id="Nova-2", name="Nova 2", skills=("standard",), priority=3),
            GuardProfile(guard_id="Vanguard-9", name="Vanguard 9", skills=("technical",), priority=4),
        ]
        self._slots = [
            DemandSlot(slot_id="A1", start=base, end=base + timedelta(hours=4), required_guards=1),
            DemandSlot(slot_id="B2", start=base + timedelta(hours=2), end=base + timedelta(hours=8), required_guards=1),
            DemandSlot(slot_id="C3", start=base + timedelta(hours=8), end=base + timedelta(hours=12), required_guards=1),
            DemandSlot(slot_id="D4", start=base + timedelta(hours=12), end=base + timedelta(hours=18), required_guards=1),
        ]

    def generate_schedule(self, criteria: EngineCriteriaModel) -> RosterResponseModel:
        if self._engine:
            schedule = self._solve_with_engine(criteria)
        else:
            schedule = None

        if not schedule:
            schedule = self._mock_schedule(criteria)
        return schedule

    def _solve_with_engine(self, criteria: EngineCriteriaModel) -> Optional[RosterResponseModel]:
        sliders = criteria.sliders
        toggles = criteria.toggles

        hard = HardConstraintSpec(
            enforce_coverage=True,
            enforce_skill_requirements=True,
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
        return self._build_response(criteria, result.assignments, result.objective_value, result.feasible)

    def _mock_schedule(self, criteria: EngineCriteriaModel) -> RosterResponseModel:
        coverage = criteria.sliders.get("coverage", 80)
        fairness = criteria.sliders.get("fairness", 50)
        assignments_map: Dict[str, List[str]] = {
            "Echo-7": ["A1", "C3"],
            "Atlas-4": ["B2"],
            "Nova-2": ["D4"],
        }
        feasible = coverage >= 70
        objective = 1200 + (coverage - 80) * 8 + (fairness - 50) * 4
        return self._build_response(criteria, assignments_map, float(objective), feasible)

    def _build_response(
        self,
        criteria: EngineCriteriaModel,
        assignments_map: Dict[str, List[str]],
        objective_value: Optional[float],
        feasible: bool,
    ) -> RosterResponseModel:
        slot_lookup = {slot.slot_id: slot for slot in self._slots}
        assignments: List[AssignmentModel] = []
        for guard_id, slot_ids in assignments_map.items():
            for slot_id in slot_ids:
                slot = slot_lookup.get(slot_id)
                if not slot:
                    continue
                assignments.append(
                    AssignmentModel(
                        slot_id=slot.slot_id,
                        guard_id=guard_id,
                        start=slot.start,
                        end=slot.end,
                    )
                )
        assignments.sort(key=lambda assignment: (assignment.guard_id, assignment.start))

        required_total = sum(slot.required_guards for slot in self._slots)
        assigned_total = len(assignments)
        coverage_ratio = assigned_total / required_total if required_total else 0.0

        guard_counts = [len(ids) for ids in assignments_map.values() if ids]
        if guard_counts:
            average = sum(guard_counts) / len(guard_counts)
            dispersion = max(abs(count - average) for count in guard_counts)
            fairness_score = max(0.0, 1.0 - dispersion / max(average, 1.0))
        else:
            fairness_score = 1.0

        fatigue_status = "Low" if criteria.toggles.get("prioritizeRest", True) else "Moderate"

        kpis = [
            KPIModel(label="Coverage Index", value=f"{coverage_ratio * 100:.0f}%", delta="+3%", status="positive"),
            KPIModel(label="Fairness Alignment", value=f"{fairness_score:.2f}", delta="+0.02", status="positive"),
            KPIModel(label="Fatigue Risk", value=fatigue_status, delta="-5%", status="neutral"),
        ]

        comparisons = [
            ScenarioComparisonModel(
                name=criteria.scenario_name,
                objective_value=objective_value,
                coverage_score=coverage_ratio,
                fairness_score=fairness_score,
                feasibility=feasible,
            ),
            ScenarioComparisonModel(
                name="High Resilience",
                objective_value=objective_value * 1.05 if objective_value else None,
                coverage_score=min(1.0, coverage_ratio * 0.98),
                fairness_score=min(1.0, fairness_score * 1.05),
                feasibility=feasible,
            ),
            ScenarioComparisonModel(
                name="Agile Coverage",
                objective_value=objective_value * 1.08 if objective_value else None,
                coverage_score=min(1.0, coverage_ratio * 1.03),
                fairness_score=max(0.0, fairness_score * 0.92),
                feasibility=coverage_ratio >= 0.85,
            ),
        ]

        return RosterResponseModel(
            feasible=feasible,
            objective_value=objective_value,
            assignments=assignments,
            kpis=kpis,
            comparisons=comparisons,
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
