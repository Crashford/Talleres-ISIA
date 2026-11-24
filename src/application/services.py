"""Casos de uso compartidos por los adaptadores primarios."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Callable
from contextlib import AbstractContextManager

from src.application.ports import IncidentRepositoryPort
from src.domain.models import TriageResult
from src.domain.sla_calculator import evaluate_sla_status
from src.domain.triage_rules import classify_incident_report


class ValidationError(ValueError):
    """Entrada inválida para un caso de uso."""


@dataclass(frozen=True)
class ActiveIncidentItem:
    incident_id: str
    title: str
    component: str
    severity: str
    status: str
    elapsed_minutes: int
    is_breached: bool
    requires_escalation: bool


@dataclass(frozen=True)
class ActiveIncidentsSummary:
    total_active: int
    breached_count: int
    incidents: list[ActiveIncidentItem]


def parse_reference_time(value: str | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    # ISO 8601 fecha y hora; no fechas solas, números ni coerciones.
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:[.,]\d+)?)?(?:Z|[+-]\d{2}:\d{2})?", value
    ):
        raise ValidationError("reference_time debe ser una fecha-hora ISO 8601.")
    try:
        return datetime.fromisoformat(value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value)
    except ValueError as error:
        raise ValidationError("reference_time no es una fecha-hora válida.") from error


class IncidentService:
    """Orquesta el dominio sin depender de transporte ni persistencia."""

    def __init__(
        self,
        repository_factory: Callable[[], AbstractContextManager[IncidentRepositoryPort]] | None = None,
    ) -> None:
        self._repository_factory = repository_factory

    def triage_incident(self, incident_id: str, raw_text: str) -> TriageResult:
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise ValidationError("El identificador no puede estar vacío y debe ser texto.")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValidationError("El reporte no puede estar vacío y debe ser texto.")
        return classify_incident_report(incident_id, raw_text)

    def get_active_incidents_summary(
        self, component_filter: str | None = None, reference_time: str | datetime | None = None
    ) -> ActiveIncidentsSummary:
        if component_filter is not None and (not isinstance(component_filter, str) or not component_filter.strip()):
            raise ValidationError("El componente no puede estar vacío.")
        reference = parse_reference_time(reference_time)
        now = datetime.now(timezone.utc) if reference is None else None
        if self._repository_factory is None:
            raise RuntimeError("El resumen requiere un repositorio.")
        with self._repository_factory() as repo:
            incidents = repo.list_active_incidents(component_filter)
        items = []
        for incident in sorted(incidents, key=lambda item: item.incident_id):
            instant = reference
            if instant is None:
                if incident.created_at.tzinfo is None:
                    instant = now.astimezone().replace(tzinfo=None)
                else:
                    instant = now.astimezone(incident.created_at.tzinfo)
            try:
                sla = evaluate_sla_status(incident, instant)
            except ValueError as error:
                raise ValidationError(str(error)) from error
            items.append(ActiveIncidentItem(
                incident.incident_id, incident.title, incident.component, incident.severity,
                incident.status, sla.elapsed_minutes, sla.is_breached, sla.requires_escalation,
            ))
        return ActiveIncidentsSummary(len(items), sum(item.is_breached for item in items), items)
