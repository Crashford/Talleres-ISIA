# AGENTS.md — IncidentOps

Trabajar desde la raíz. Python >=3.10, uv. Consultar docs/ROADMAP.md, docs/constitution.md y docs/adr/ para decisiones, specs/ para contratos.

## Estructura operativa (H001)
- src/domain/: modelos, triaje determinista y cálculo SLA.
- src/application/services.py: caso de uso de triaje compartido.
- src/adapters/inbound/api/: FastAPI, esquemas y create_app.
- src/adapters/inbound/cli.py: CLI Typer.
- src/incident_repository.py: benchmark SQLite heredado; migración pendiente H002.
- src/context_audit.py: auditoría de contexto, búsqueda recursiva de Python.
- data/: muestras; tests/: regresión y BDD; evidence/: evidencias históricas.

## Comandos

```sh
uv sync
uv run pytest -v
uv run python -m src.domain.triage_rules
uv run python -m src.domain.sla_calculator
uv run python -m src.incident_repository --records 10000
uv run python -m src.context_audit --symbol classify_incident_report
uv run python -m src.adapters.inbound.cli triage --incident-id INC-1001 --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"
uv run uvicorn src.adapters.inbound.api.app:app
```

## Trabajo del agente
Plan: leer, aclarar requisitos y proponer tareas sin editar. Build: ejecutar exclusivamente lo aprobado y verificar. Conservar regresiones y ADR históricos; reportar evidencia real y limitaciones. Mantener este archivo operativo.
