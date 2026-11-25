"""Casos de uso compartidos por los adaptadores primarios."""

import secrets
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Callable
from contextlib import AbstractContextManager

from src.application.dtos import IncidentCreatedResult, IncidentSLAResult
from src.application.ports import IncidentRepositoryPort
from src.domain.models import Incident, TriageResult
from src.domain.sla_calculator import (
    evaluate_sla_status,
    resolve_created_at,
    resolve_reference_time,
)
from src.domain.triage_rules import classify_incident_report

INITIAL_STATUSES = ("OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED")


class ValidationError(ValueError):
    """Entrada inválida para un caso de uso."""


class IncidentNotFoundError(LookupError):
    """El incidente consultado no existe."""


class PersistentStorageUnavailableError(RuntimeError):
    """La configuración no conserva datos entre operaciones."""


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


class IncidentService:
    """Orquesta el dominio sin depender de transporte ni persistencia."""

    def __init__(
        self,
        repository_factory: Callable[[], AbstractContextManager[IncidentRepositoryPort]] | None = None,
    ) -> None:
        self._repository_factory = repository_factory

    def check_health(self) -> bool:
        if self._repository_factory is None:
            return False
        try:
            with self._repository_factory() as repo:
                return repo.check_health()
        except Exception:
            return False

    def triage_incident(self, incident_id: str, raw_text: str) -> TriageResult:
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise ValidationError("El identificador no puede estar vacío y debe ser texto.")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValidationError("El reporte no puede estar vacío y debe ser texto.")
        return classify_incident_report(incident_id, raw_text)

    def create_incident(
        self,
        title: str,
        raw_text: str,
        incident_id: str | None = None,
        created_at: str | datetime | None = None,
        status: str | None = None,
    ) -> IncidentCreatedResult:
        if self._repository_factory is None:
            raise RuntimeError("El alta requiere un repositorio.")
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("El título no puede estar vacío y debe ser texto.")
        initial_status = status if status is not None else "OPEN"
        if initial_status not in INITIAL_STATUSES:
            raise ValidationError("El estado inicial debe ser OPEN, IN_PROGRESS o ESCALATION_REQUIRED.")
        if incident_id is None:
            ident = "INC-" + secrets.token_hex(4).upper()
        elif isinstance(incident_id, str) and incident_id.strip():
            ident = incident_id
        else:
            raise ValidationError("El identificador no puede estar vacío y debe ser texto.")
        try:
            created = resolve_created_at(created_at)
        except ValueError as error:
            raise ValidationError(str(error)) from error

        with self._repository_factory() as repo:
            if not repo.supports_persistent_writes():
                raise PersistentStorageUnavailableError(
                    "La configuración de almacenamiento no conserva datos entre operaciones; "
                    "defina DATABASE_URL con un archivo SQLite."
                )
            triage = self.triage_incident(ident, raw_text)
            incident = Incident(
                ident, title, triage.component, triage.severity, initial_status, created,
                None, triage.recommended_team, triage.duplicate_group_key,
            )
            if not repo.save_incident(incident):
                raise ValidationError("El identificador ya existe; el incidente original no se modificó.")
            duplicate_of = (
                repo.find_open_duplicates(triage.duplicate_group_key, ident)
                if triage.duplicate_group_key else []
            )
        return IncidentCreatedResult(
            incident_id=incident.incident_id,
            title=incident.title,
            component=incident.component,
            severity=incident.severity,
            created_at=incident.created_at,
            status=incident.status,
            resolved_at=incident.resolved_at,
            recommended_team=incident.recommended_team,
            duplicate_group_key=incident.duplicate_group_key,
            rationale=triage.rationale,
            consistency_ratio=triage.consistency_ratio,
            is_duplicate=bool(duplicate_of),
            duplicate_of=duplicate_of,
        )

    def evaluate_incident_sla(
        self, incident_id: str, reference_time: str | datetime | None = None
    ) -> IncidentSLAResult:
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise ValidationError("El identificador no puede estar vacío y debe ser texto.")
        if self._repository_factory is None:
            raise RuntimeError("La auditoría SLA requiere un repositorio.")
        with self._repository_factory() as repo:
            incident = repo.get_incident(incident_id)
            if incident is None:
                raise IncidentNotFoundError(f"No existe el incidente {incident_id}.")
            try:
                reference = resolve_reference_time(incident.created_at, reference_time, incident.severity)
                evaluation = evaluate_sla_status(incident, reference)
            except ValueError as error:
                raise ValidationError(str(error)) from error
        return IncidentSLAResult(
            incident_id=incident.incident_id,
            reference_time=reference,
            elapsed_minutes=evaluation.elapsed_minutes,
            allowed_minutes=evaluation.allowed_minutes,
            remaining_minutes=evaluation.remaining_minutes,
            is_breached=evaluation.is_breached,
            requires_escalation=evaluation.requires_escalation,
        )

    def get_active_incidents_summary(
        self, component_filter: str | None = None, reference_time: str | datetime | None = None
    ) -> ActiveIncidentsSummary:
        if component_filter is not None and (not isinstance(component_filter, str) or not component_filter.strip()):
            raise ValidationError("El componente no puede estar vacío.")
        if self._repository_factory is None:
            raise RuntimeError("El resumen requiere un repositorio.")
        with self._repository_factory() as repo:
            incidents = repo.list_active_incidents(component_filter)
        items = []
        for incident in sorted(incidents, key=lambda item: item.incident_id):
            try:
                instant = resolve_reference_time(incident.created_at, reference_time, incident.severity)
                sla = evaluate_sla_status(incident, instant)
            except ValueError as error:
                raise ValidationError(str(error)) from error
            items.append(ActiveIncidentItem(
                incident.incident_id, incident.title, incident.component, incident.severity,
                incident.status, sla.elapsed_minutes, sla.is_breached, sla.requires_escalation,
            ))
        return ActiveIncidentsSummary(len(items), sum(item.is_breached for item in items), items)
