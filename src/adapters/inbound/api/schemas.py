"""Contratos de entrada y salida HTTP."""

from pydantic import BaseModel, StrictStr


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
