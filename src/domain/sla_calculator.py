"""Cálculo determinista de SLA: 24/7 (P0/P1) y horario hábil (P2/P3).

Ventana hábil: lunes a viernes [08:00, 18:00), sin feriados configurados.
La duración se acumula en segundos y se convierte a minutos completos al final.
"""

import re
from datetime import datetime, time, timedelta
from typing import Dict

from src.domain.models import Incident, SLAEvaluation, SLARule, SeverityLevel

SLA_POLICY_TABLE: Dict[SeverityLevel, SLARule] = {
    "P0": SLARule(severity="P0", max_resolution_minutes=60, operates_24x7=True),
    "P1": SLARule(severity="P1", max_resolution_minutes=240, operates_24x7=True),
    "P2": SLARule(severity="P2", max_resolution_minutes=480, operates_24x7=False),
    "P3": SLARule(severity="P3", max_resolution_minutes=1440, operates_24x7=False),
}

BUSINESS_START = time(8, 0)
BUSINESS_END = time(18, 0)
ISO_DATETIME = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:[.,]\d+)?)?(?:Z|[+-]\d{2}:\d{2})?"
)


def parse_iso_datetime(value: str | datetime) -> datetime:
    """Convierte una fecha-hora ISO 8601 sin aceptar fechas solas ni formatos libres."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not ISO_DATETIME.fullmatch(value):
        raise ValueError("La fecha-hora debe estar en formato ISO 8601.")
    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(normalized.replace(",", "."))
    except ValueError as error:
        raise ValueError("La fecha-hora ISO 8601 no es válida.") from error


def resolve_created_at(value: str | datetime | None = None) -> datetime:
    """Usa el instante local aware del entorno cuando el alta omite created_at."""
    if value is None:
        return datetime.now().astimezone()
    return parse_iso_datetime(value)


def resolve_reference_time(
    created_at: str | datetime,
    reference_time: str | datetime | None = None,
    severity: SeverityLevel | None = None,
) -> datetime:
    """Resuelve una referencia compatible con la convención temporal del incidente."""
    created = parse_iso_datetime(created_at)
    if reference_time is None:
        if created.tzinfo is None:
            return datetime.now().astimezone().replace(tzinfo=None)
        return datetime.now().astimezone(created.tzinfo)
    reference = parse_iso_datetime(reference_time)
    if (created.tzinfo is None) != (reference.tzinfo is None):
        raise ValueError("Las fechas deben ser ambas naive o ambas timezone-aware.")
    if (
        created.tzinfo is not None
        and severity in ("P2", "P3")
        and created.utcoffset() != reference.utcoffset()
    ):
        raise ValueError("Las marcas P2/P3 deben usar el mismo offset fijo.")
    if reference < created:
        raise ValueError("La referencia no puede ser anterior a la creación.")
    return reference


def get_sla_rule_for_severity(severity: SeverityLevel) -> SLARule:
    """Recupera una política conocida; rechaza valores fuera del dominio."""
    if severity not in SLA_POLICY_TABLE:
        raise ValueError(f"Severidad no válida: {severity}")
    return SLA_POLICY_TABLE[severity]


def _business_elapsed_seconds(start: datetime, end: datetime) -> float:
    """Suma intersecciones con jornadas hábiles en O(D) y memoria O(1)."""
    elapsed_seconds = 0.0
    day = start.date()
    while day <= end.date():
        if day.weekday() < 5:
            begin = datetime.combine(day, BUSINESS_START, tzinfo=start.tzinfo)
            finish = datetime.combine(day, BUSINESS_END, tzinfo=start.tzinfo)
            overlap_start = max(start, begin)
            overlap_end = min(end, finish)
            if overlap_end > overlap_start:
                elapsed_seconds += (overlap_end - overlap_start).total_seconds()
        day += timedelta(days=1)
    return elapsed_seconds


def evaluate_sla_status(incident: Incident, reference_time: datetime) -> SLAEvaluation:
    """Evalúa minutos consumidos, incumplimiento y alerta preventiva.

    Para incidentes resueltos se utiliza resolved_at como tiempo de cierre y no
    se dispara escalamiento; el estado de incumplimiento histórico permanece.
    El escalamiento se mantiene activo tras un incumplimiento mientras no se
    resuelva. Minutos son duraciones completas (floor de segundos / 60).
    """
    rule = get_sla_rule_for_severity(incident.severity)
    if incident.status == "RESOLVED" and incident.resolved_at is None:
        raise ValueError("Un incidente RESOLVED requiere resolved_at")
    end_time = incident.resolved_at if incident.status == "RESOLVED" else reference_time
    if (incident.created_at.tzinfo is None) != (end_time.tzinfo is None):
        raise ValueError("Ambas fechas deben ser naive o ambas timezone-aware")
    if end_time < incident.created_at:
        raise ValueError("El tiempo de evaluación/cierre no puede ser anterior a la creación")
    if rule.operates_24x7:
        elapsed_seconds = (end_time - incident.created_at).total_seconds()
    else:
        # La política opera con jornadas locales; incidentes aware deben llegar
        # normalizados a la misma zona horaria (sin cambios de DST dentro del tramo).
        if (incident.created_at.tzinfo is not None and
                incident.created_at.utcoffset() != end_time.utcoffset()):
            raise ValueError("Normaliza ambas marcas a una misma zona local de offset fijo")
        elapsed_seconds = _business_elapsed_seconds(incident.created_at, end_time)
    elapsed_minutes = int(elapsed_seconds // 60)
    remaining_minutes = rule.max_resolution_minutes - elapsed_minutes
    is_breached = elapsed_minutes > rule.max_resolution_minutes
    requires_escalation = (
        incident.status != "RESOLVED"
        and elapsed_seconds >= rule.max_resolution_minutes * rule.escalation_threshold_ratio * 60
    )
    return SLAEvaluation(
        incident_id=incident.incident_id,
        severity=incident.severity,
        elapsed_minutes=elapsed_minutes,
        allowed_minutes=rule.max_resolution_minutes,
        remaining_minutes=remaining_minutes,
        is_breached=is_breached,
        requires_escalation=requires_escalation,
    )


def _run_demo() -> None:
    """Casos comprobables, incluyendo fin de semana y umbrales."""
    cases = [
        ("P2", datetime(2026, 11, 6, 17), datetime(2026, 11, 9, 9), 120),
        ("P2", datetime(2026, 11, 6, 18, 30), datetime(2026, 11, 9, 8, 30), 30),
        ("P3", datetime(2026, 11, 7, 12), datetime(2026, 11, 9, 9), 60),
        ("P2", datetime(2026, 11, 9, 16), datetime(2026, 11, 10, 12), 360),
        ("P0", datetime(2026, 11, 6, 17), datetime(2026, 11, 9, 9), 3840),
        ("P1", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 11), 180),
    ]
    print("=== Validación demostrativa de SLA ===")
    for index, (sev, created, checked, expected) in enumerate(cases, 1):
        incident = Incident(f"DEMO-{index}", "Prueba SLA", "reporting-api", sev, "OPEN", created)
        result = evaluate_sla_status(incident, checked)
        assert result.elapsed_minutes == expected, (index, result.elapsed_minutes, expected)
        print(f"{incident.incident_id}: {sev}, minutos={result.elapsed_minutes}, "
              f"esperados={expected}, escalamiento={result.requires_escalation}, "
              f"incumplido={result.is_breached} OK")


if __name__ == "__main__":
    _run_demo()
