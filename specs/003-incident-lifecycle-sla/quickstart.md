# Quickstart — H003: ciclo de vida, duplicados y SLA

**Spec**: [spec.md](spec.md) | **Contrato**: [contracts/incidents.md](contracts/incidents.md) | **Estado**: curado con D01–D05, H06–H08 y Analyze-A1–A7; comandos documentados, no ejecutados en la curaduría.

La rama Git activa es `practica-guiada-sdd-semana-2`. `tasks.md` está curado y aprobado; no se implementó código y no se ejecutaron pruebas.

## Requisitos

- Python >=3.10 y `uv`.
- Dependencias del proyecto ya sincronizadas.

## Instalación

```powershell
uv sync --locked
```

## Calidad y regresiones

```powershell
uv run ruff check src/
uv run pytest -v
```

Criterio esperado en Build: Ruff sin infracciones; 51 pruebas y 10 subpruebas de la línea base más los 15 escenarios E001–E015.

## Almacenamiento (D05/H08)

El default `sqlite:///:memory:` se conserva para desarrollo y regresiones, pero no conserva datos entre operaciones y por eso el alta se rechaza con 503/código 1. Para registrar y auditar, defina un archivo SQLite:

```powershell
$env:DATABASE_URL = "sqlite:///incidentops.db"
```

La variable es por terminal. Si abre otra terminal, vuelva a definirla antes de usar REST o CLI.

## Servidor REST

En una terminal con `DATABASE_URL` configurado:

```powershell
uv run uvicorn src.adapters.inbound.api.app:app
```

## Verificación manual REST

### E001 — Alta P0 válida

```powershell
$body = @{
  title    = "HTTP 502 en pasarela de pagos"
  raw_text = "HTTP 502 Bad Gateway en pasarela de pagos"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/incidents" `
  -Method Post -ContentType "application/json" -Body $body
```

Se espera 201 Created, ID autogenerado `INC-HEX8`, `created_at` con offset local, `status: "OPEN"`, clasificación completa, `is_duplicate: false` y `duplicate_of: []`. `raw_text` solo alimenta el triaje y no aparece en la respuesta.

### E003/E004 — Aviso de duplicados

Repita el alta con otro `title` y un `raw_text` que produzca la misma `duplicate_group_key`. Se espera 201 Created con `is_duplicate: true` y el ID anterior en `duplicate_of` mientras esté en OPEN, IN_PROGRESS o ESCALATION_REQUIRED; no se usa HTTP 409. Un incidente RESOLVED o una clave distinta no genera aviso.

### E014 — Alta P2 determinista con ID propio

El ID P2 es distinto del P0 anterior (H06):

```powershell
$body = @{
  title       = "Latencia alta en API pública"
  raw_text    = "Latencia alta sostenida en la API pública sin pérdida de servicio"
  incident_id = "INC-P2F4E6A8"
  created_at  = "2026-11-06T17:00:00"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/incidents" `
  -Method Post -ContentType "application/json" -Body $body
```

Se espera 201 Created con `created_at` respetado. Ambas marcas naive usan la convención ADR-002; la paridad determinista depende de fechas explícitas (D02).

### E005/E006/E008 — Auditoría P2 determinista

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/incidents/INC-P2F4E6A8/sla?reference_time=2026-11-09T09:00:00" `
  -Method Get
```

Se espera 200 OK:

```json
{
  "incident_id": "INC-P2F4E6A8",
  "reference_time": "2026-11-09T09:00:00",
  "elapsed_minutes": 120,
  "allowed_minutes": 480,
  "remaining_minutes": 360,
  "is_breached": false,
  "requires_escalation": false
}
```

### E002/E009/E010/E012/E013 — Errores

- `title` o `raw_text` vacío: 422.
- ID inexistente en `/sla`: 404.
- `reference_time` inválido, anterior a `created_at`, naive/aware mezclado u offset distinto en P2/P3: 422.
- `status: "RESOLVED"` o desconocido en el alta: 422.
- ID existente en el alta, incluso en concurrencia: 422 y registro original intacto; sin HTTP 409.

## Verificación manual CLI

En otra terminal con el mismo archivo para consultas (H08):

```powershell
$env:DATABASE_URL = "sqlite:///incidentops.db"

uv run python -m src.adapters.inbound.cli create `
  --title "HTTP 502 en pasarela de pagos" `
  --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"

uv run python -m src.adapters.inbound.cli sla `
  --incident-id "INC-P2F4E6A8" `
  --reference-time "2026-11-09T09:00:00"
```

Se espera código `0` y JSON equivalente a REST.

### E014 — Paridad de creación con almacenamiento aislado equivalente

Use otro archivo para repetir la misma creación P2 con ID y fecha explícitos:

```powershell
$env:DATABASE_URL = "sqlite:///incidentops-cli-parity.db"
uv run python -m src.adapters.inbound.cli create `
  --title "Latencia alta en API pública" `
  --raw-text "Latencia alta sostenida en la API pública sin pérdida de servicio" `
  --incident-id "INC-P2F4E6A8" `
  --created-at "2026-11-06T17:00:00"
```

Comparado con el alta REST del mismo ID/fecha, deben coincidir identificador, fecha, clasificación, `is_duplicate` y `duplicate_of`.

### E015 — Rechazo de almacenamiento efímero

```powershell
$env:DATABASE_URL = "sqlite:///:memory:"
uv run python -m src.adapters.inbound.cli create `
  --title "HTTP 502 en pasarela de pagos" `
  --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"
$LASTEXITCODE
```

Se espera código `1`, sin ID ni éxito falso. El equivalente REST responde 503.

## Cobertura BDD

| ID | Escenario | Verificación principal |
|---|---|---|
| E001 | Alta válida | 201/JSON, ID autogenerado, fecha local, OPEN y sin duplicado. |
| E002 | Entrada vacía | 422/código 1 sin persistir. |
| E003 | Duplicado abierto | 201 con `is_duplicate: true` y `duplicate_of` correcto; no 409. |
| E004 | Sin duplicado | RESOLVED o sin coincidencia no genera aviso. |
| E005 | Auditoría | Cinco valores de SLA y `reference_time` efectivo. |
| E006 | Caso P2 | 120/480/360, `false`, `false`, con ID propio. |
| E007 | Resuelto | Cálculo hasta `resolved_at`, sin escalamiento ni reconstrucción. |
| E008 | Paridad SLA | Mismo archivo SQLite, incidente y referencia. |
| E009 | ID inexistente | 404/código 1. |
| E010 | Referencia inválida | 422/código 1. |
| E011 | ID repetido | 422/código 1, concurrencia, sin sobrescritura ni HTTP 409. |
| E012 | Fechas incompatibles | 422/código 1; referencia omitida compatible. |
| E013 | Estado inicial inválido | RESOLVED/desconocido rechazado. |
| E014 | Paridad de creación | Almacenamientos aislados equivalentes. |
| E015 | Almacenamiento efímero | 503/código 1 sin falso éxito. |

## Regresiones H002 (H07)

El resumen H002 (`uv run python -m src.adapters.inbound.cli summary`) permanece con OPEN e IN_PROGRESS. Si una prueba de `tests/test_spec_002_summary.py` falla por la extensión de `Incident` o por la capacidad del puerto, ajuste solo la preparación de la fixture; no elimine pruebas ni debilite aserciones. En concreto, revise `tests/test_spec_002_summary.py::test_repository_port_and_sql` durante Build.
