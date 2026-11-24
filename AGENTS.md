# AGENTS.md — IncidentOps

Trabajar desde la raíz. Python >=3.10, uv. Consultar docs/ROADMAP.md, .specify/memory/constitution.md y docs/adr/ para decisiones, specs/ para contratos.

## Estructura operativa (H001 y H002)
- src/domain/: modelos, triaje determinista y cálculo SLA.
- src/application/services.py: casos de uso compartidos de triaje y resumen.
- src/adapters/inbound/api/: FastAPI, esquemas y create_app.
- src/adapters/inbound/cli.py: CLI Typer.
- src/application/ports.py: puerto secundario de persistencia.
- src/adapters/outbound/: fábrica DATABASE_URL y adaptador SQLite.
- src/incident_repository.py: benchmark sobre el adaptador optimizado.
- src/context_audit.py: auditoría de contexto, búsqueda recursiva de Python.
- data/: muestras; tests/: regresión y BDD; evidence/: evidencias históricas.

## Comandos

```sh
uv sync
uv run ruff check src/
uv run pytest -v
uv run python -m src.domain.triage_rules
uv run python -m src.domain.sla_calculator
uv run python -m src.incident_repository --records 10000
uv run python -m src.context_audit --symbol classify_incident_report
uv run python -m src.adapters.inbound.cli triage --incident-id INC-1001 --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"
uv run python -m src.adapters.inbound.cli summary
uv run uvicorn src.adapters.inbound.api.app:app
```

## Trabajo del agente
Plan: leer, aclarar requisitos y proponer tareas sin editar. Build: ejecutar exclusivamente lo aprobado y verificar. Conservar regresiones y ADR históricos; reportar evidencia real y limitaciones. Mantener este archivo operativo.

DATABASE_URL por defecto sqlite:///:memory: (vacío); para compartir datos REST/CLI indicar un archivo SQLite. Skills en .opencode/skills/ y especificación H002 en specs/002-active-incidents-summary/.
