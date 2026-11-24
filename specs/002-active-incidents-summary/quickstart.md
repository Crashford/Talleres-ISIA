# Quickstart — H002

Desde la raíz:

```sh
uv sync
uv run ruff check src/
uv run pytest -v
uv run python -m src.domain.triage_rules
uv run python -m src.domain.sla_calculator
uv run python -m src.adapters.inbound.cli triage --incident-id INC-1001 --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"
uv run python -m src.adapters.inbound.cli summary
uv run python -m src.incident_repository --records 10000
uv run uvicorn src.adapters.inbound.api.app:app
```

Sin DATABASE_URL, la consulta de resumen devuelve vacío. Para consultar una BD SQLite existente, configurar DATABASE_URL=sqlite:///incidentops.db en ambos procesos. No se añade endpoint para sembrar o registrar incidentes; las pruebas crean datos de forma aislada. Swagger: http://127.0.0.1:8000/docs.
