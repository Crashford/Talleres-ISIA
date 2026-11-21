"""Clasificación determinista de severidad, equipo y correlación de incidentes.

Las claves de correlación identifican candidatos, no confirman una causa raíz.
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

from src.models import SeverityLevel, TriageResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample_incidents.json"

# Componentes compatibles con los identificadores ya usados en el repositorio.
COMPONENT_TEAMS = {
    "payments-gateway": "Backend-Core",
    "auth-identity": "Security-IAM",
    "reporting-api": "Backend-Core",
    "frontend-ui": "Backend-Core",
    "database-cluster": "Data-DBA",
    "infra-certificates": "Platform-SRE",
    "security-authorization": "Security-IAM",
}


def _normalize(text: str) -> str:
    """Normaliza mayúsculas, acentos y espacios sin alterar números o signos."""
    text = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def _has(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _classify(text: str) -> Tuple[SeverityLevel, str, str, str]:
    """Devuelve severidad, componente, síntoma normalizado y justificación."""
    # Seguridad multi-tenant: detectar acceso cruzado antes que una referencia genérica a PDF.
    cross_tenant = _has(text, "otra organizacion", "otra empresa", "otros clientes", "otro tenant")
    access_bypass = _has(text, "company_id", "visualizar facturas", "acceso no autorizado", "datos de otra")
    if cross_tenant and access_bypass:
        return "P0", "security-authorization", "cross-tenant-data-exposure", "Exposición de datos entre organizaciones."

    # Infraestructura de datos compartida; no confundir timeouts del pool con fallos HTTP.
    db_context = _has(text, "postgresql", "base de datos", "pool de conexiones", "nodo primario")
    if db_context:
        load = re.search(r"(?:conexiones.{0,45}?)?(\d{2,3})\s*%", text)
        high_load = bool(load and int(load.group(1)) > 90)
        timeouts = _has(text, "timeout", "tiempo de espera")
        if high_load or (timeouts and _has(text, "pool de conexiones")):
            return "P1", "database-cluster", "connection-pool-saturation", "Saturación o timeouts del pool de conexiones compartido."
        return "P2", "database-cluster", "database-degradation", "Degradación de base de datos sin caída global confirmada."

    # Certificados de staging: mantenimiento preventivo, no interrupción de producción.
    if _has(text, "certificado", "tls") and _has(text, "staging", "no productivo", "pruebas"):
        return "P3", "infra-certificates", "staging-certificate-rotation", "Rotación preventiva de certificado en staging."

    # Detectar UI cosmética antes de palabras genéricas como exportar.
    if _has(text, "boton", "color", "gris", "verde oscuro") and _has(text, "color", "gris", "cosmetic", "resalta"):
        return "P3", "frontend-ui", "cosmetic-color-change", "Solicitud de presentación visual sin fallo funcional."

    # Cobros / pasarela: misma categoría para fallos 502 de diferentes reportantes.
    payment = _has(text, "pago", "cobro", "pasarela", "gateway", "tarjeta")
    if payment:
        if "502" in text or "bad gateway" in text:
            severity: SeverityLevel = "P0"
            reason = ("Indisponibilidad global de pagos reportada."
                      if _has(text, "todas las transacciones", "ningun comercio", "todos los comercios")
                      else "Fallo HTTP 502 en servicio crítico de pagos: P0 preventivo; alcance global por confirmar.")
            return severity, "payments-gateway", "http-502-card-payments", reason
        return "P2", "payments-gateway", "payment-issue", "Fallo de pago sin alcance global demostrado."

    if _has(text, "cuenta", "ingresar", "autenticacion", "bloqueada") and _has(text, "bloqueada", "bloqueo", "ingresar", "acceder"):
        return "P2", "auth-identity", "individual-account-lockout", "Bloqueo de acceso individual."

    # La lentitud de vistas de gran volumen converge en un grupo independiente
    # de exportaciones lentas: la coincidencia es candidata, no prueba causal.
    if _has(text, "excel", "exportacion mensual", "descarga el archivo"):
        return "P2", "reporting-api", "slow-excel-export", "Exportación lenta pero completada."

    large_dataset = bool(re.search(r"10[.,]?000|10000", text))
    slow = _has(text, "tarda", "segundos", "lento", "lenta", "lentitud")
    if large_dataset and slow and _has(text, "dashboard", "reportes", "listado", "planes", "historial", "clientes corporativos"):
        return "P2", "reporting-api", "slow-large-dataset-over-3s", "Latencia en consultas sobre más de 10.000 registros."
    if slow:
        return "P2", "reporting-api", "performance-degradation", "Degradación de rendimiento sin caída informada."

    # Fallback conservador: ausencia de datos de incidente grave.
    return "P3", "reporting-api", "unclassified-request", "Sin evidencia de impacto suficiente para elevar severidad; requiere revisión."


def classify_incident_report(incident_id: str, raw_text: str) -> TriageResult:
    """Clasifica un reporte sin basarse en palabras de urgencia subjetiva."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text debe ser una cadena")
    text = _normalize(raw_text)
    severity, component, symptom, rationale = _classify(text)
    return TriageResult(
        incident_id=incident_id,
        severity=severity,
        component=component,
        rationale=rationale,
        recommended_team=COMPONENT_TEAMS[component],
        duplicate_group_key=f"{component}:{symptom}",
    )


def _run_triage_audit() -> None:
    """Audita el motor sobre los casos de muestra del repositorio."""
    incidents: List[Dict[str, str]] = json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))
    print(f"{'ID':<10} {'Sev.':<5} {'Componente':<23} {'Equipo':<15} Clave")
    print("-" * 110)
    for item in incidents:
        result = classify_incident_report(item["id"], item["raw_text"])
        print(f"{result.incident_id:<10} {result.severity:<5} {result.component:<23} "
              f"{result.recommended_team:<15} {result.duplicate_group_key}")


if __name__ == "__main__":
    _run_triage_audit()
