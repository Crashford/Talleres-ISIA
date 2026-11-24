# AGENTS.md — IncidentOps

## Estado operativo (Semana 1)
Proyecto Python >= 3.10 gestionado con uv. Trabajar desde la raíz del repositorio; `pyproject.toml` declara tiktoken para auditoría de contexto.

| Ruta | Responsabilidad actual |
|---|---|
| `src/models.py` | Entidades y tipos de incidentes, SLA y triaje. |
| `src/triage_rules.py` | Clasificación determinista, enrutamiento y claves de correlación. |
| `src/sla_calculator.py` | Cálculo determinista de SLA y escalamiento. |
| `src/incident_repository.py` | Repositorio SQLite en memoria por defecto y benchmark de consultas. |
| `src/context_audit.py` | Auditoría de consumo de tokens. |
| `data/sample_incidents.json` | Casos de muestra. |
| `tests/` | Regresiones de triaje y SLA con unittest. |
| `docs/adr/` | Decisiones arquitectónicas y plantilla. |
| `evidence/`, `CONTEXT_LOG.md` | Evidencias y registro de contexto de Semana 1. |

## Comandos
```sh
uv sync
uv run python -m src.triage_rules
uv run python -m src.sla_calculator
uv run python -m src.incident_repository --records 10000
uv run python -m unittest discover -s tests -v
uv run python -m src.context_audit --symbol classify_incident_report
```

## Flujo del agente
- Plan: inspeccionar archivos y pruebas, identificar ambigüedades, proponer decisiones y tareas sin modificar código.
- Build: aplicar únicamente el plan aprobado; ejecutar verificaciones y reportar resultados reales.
- Conservar pruebas y evidencia heredadas; no reescribir ADR históricos. Registrar nuevas decisiones en docs/adr/.
- Actualizar este manual cuando cambien estructura o comandos. Mantener las decisiones de producto y arquitectura en sus documentos correspondientes.
