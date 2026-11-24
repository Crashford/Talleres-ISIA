# Contract — H002

## HTTP

GET /api/v1/incidents/summary?component=payments-gateway&reference_time=2026-11-09T10:00:00

Ambos parámetros opcionales. HTTP 200: JSON con total_active (entero), breached_count (entero), incidents (lista). Cada item: incident_id, title, component, severity, status, elapsed_minutes, is_breached y requires_escalation. Vacío:

```json
{"total_active":0,"breached_count":0,"incidents":[]}
```

## CLI

```sh
uv run python -m src.adapters.inbound.cli summary --component payments-gateway --reference-time 2026-11-09T10:00:00
```

Mismo JSON en stdout y código 0. Parámetros opcionales. Entrada inválida: HTTP 422 o mensaje stderr y código 1 para CLI. Las reglas temporales y el filtro exacto se describen en research.md, aprobados antes de Build.

El POST /api/v1/incidents/triage y su CLI no cambian.
