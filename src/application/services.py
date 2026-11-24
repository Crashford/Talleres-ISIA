"""Casos de uso compartidos por los adaptadores primarios."""

from src.domain.models import TriageResult
from src.domain.triage_rules import classify_incident_report


class ValidationError(ValueError):
    """Entrada inválida para un caso de uso."""


class IncidentService:
    """Orquesta el dominio sin depender de transporte ni persistencia."""

    def triage_incident(self, incident_id: str, raw_text: str) -> TriageResult:
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise ValidationError("El identificador no puede estar vacío y debe ser texto.")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValidationError("El reporte no puede estar vacío y debe ser texto.")
        return classify_incident_report(incident_id, raw_text)
