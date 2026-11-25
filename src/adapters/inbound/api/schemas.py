"""Contratos de entrada y salida HTTP."""

from datetime import datetime

from pydantic import BaseModel, StrictStr


class HealthResponse(BaseModel):
    status: str
    database: str


class TriageRequest(BaseModel):
    incident_id: StrictStr
    raw_text: StrictStr


class TriageResponse(BaseModel):
    incident_id: str
    severity: str
    component: str
    rationale: str
    consistency_ratio: float
    recommended_team: str
    duplicate_group_key: str

class ActiveIncidentItem(BaseModel):
    incident_id: str
    title: str
    component: str
    severity: str
    status: str
    elapsed_minutes: int
    is_breached: bool
    requires_escalation: bool


class ActiveIncidentsSummaryResponse(BaseModel):
    total_active: int
    breached_count: int
    incidents: list[ActiveIncidentItem]


class CreateIncidentRequest(BaseModel):
    title: StrictStr
    raw_text: StrictStr
    incident_id: str | None = None
    created_at: str | None = None
    status: str | None = None


class IncidentCreatedResponse(BaseModel):
    incident_id: str
    title: str
    component: str
    severity: str
    created_at: datetime
    status: str
    resolved_at: datetime | None
    recommended_team: str | None
    duplicate_group_key: str | None
    rationale: str
    consistency_ratio: float
    is_duplicate: bool
    duplicate_of: list[str]


class SLAEvaluationResponse(BaseModel):
    incident_id: str
    reference_time: datetime
    elapsed_minutes: int
    allowed_minutes: int
    remaining_minutes: int
    is_breached: bool
    requires_escalation: bool
