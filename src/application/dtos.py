"""DTOs de aplicación: independientes de Pydantic y de los adaptadores."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.models import IncidentStatus, SeverityLevel, TeamName


@dataclass(frozen=True)
class IncidentCreatedResult:
    incident_id: str
    title: str
    component: str
    severity: SeverityLevel
    created_at: datetime
    status: IncidentStatus
    resolved_at: Optional[datetime]
    recommended_team: Optional[TeamName]
    duplicate_group_key: Optional[str]
    rationale: str
    consistency_ratio: float
    is_duplicate: bool
    duplicate_of: list[str]


@dataclass(frozen=True)
class IncidentSLAResult:
    incident_id: str
    reference_time: datetime
    elapsed_minutes: int
    allowed_minutes: int
    remaining_minutes: int
    is_breached: bool
    requires_escalation: bool
