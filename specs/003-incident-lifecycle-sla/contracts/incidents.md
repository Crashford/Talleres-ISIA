# Contracts — H003: ciclo de vida, duplicados y SLA

**Spec**: [spec.md](spec.md) | **Estado**: curado con D01–D05, H06–H08 y Analyze-A1–A7; contrato observable de REST y CLI

> Las operaciones de alta requieren almacenamiento que conserve datos entre operaciones. Configure `DATABASE_URL` con un archivo SQLite antes de registrar. `sqlite:///:memory:` sigue siendo el valor por defecto, pero el alta responde 503/código 1 en ese modo.

## Alcance

| Operación | REST | CLI | Éxito | Errores |
|---|---|---|---|---|
| Registrar incidente | `POST /api/v1/incidents` | `create` | 201 Created / JSON | 422, 503 / código 1 |
| Auditar SLA | `GET /api/v1/incidents/{incident_id}/sla` | `sla` | 200 / JSON | 404, 422 / código 1 |

Los códigos de salida CLI son `0` para éxito y `1` para cualquier error de aplicación. Las respuestas exitosas son JSON equivalente en ambas interfaces; el orden de claves no es parte del contrato.

## Configuración previa

```powershell
$env:DATABASE_URL = "sqlite:///incidentops.db"
uv run uvicorn src.adapters.inbound.api.app:app
```

En otra terminal del mismo directorio:

```powershell
$env:DATABASE_URL = "sqlite:///incidentops.db"
```

La variable es por sesión: un terminal nuevo sin esa variable usa `sqlite:///:memory:` y no puede registrar incidentes.

## Tipos compartidos

### Cuerpo de alta

```json
{
  "title": "string no vacío",
  "raw_text": "string no vacío",
  "incident_id": "INC-A1B2C3D4",
  "created_at": "2026-11-06T17:00:00",
  "status": "OPEN"
}
```

- `title` y `raw_text`: obligatorios, no vacíos ni compuestos solo por espacios.
- `incident_id`: opcional. Si se omite, se genera `INC-HEX8`. Si se proporciona, debe ser texto no vacío; no se valida formato para IDs entrantes. Un ID existente se rechaza sin sobrescribir, incluso en altas concurrentes (D01/D03).
- `created_at`: opcional. Si se omite, se usa `datetime.now().astimezone()`, con offset local del entorno (D02). Las fechas explícitas se respetan.
- `status`: opcional, `OPEN` por defecto. Valores iniciales válidos: `OPEN`, `IN_PROGRESS`, `ESCALATION_REQUIRED`. `RESOLVED` y desconocidos se rechazan (D03).

### Respuesta de alta

```json
{
  "incident_id": "INC-A1B2C3D4",
  "title": "HTTP 502 en pasarela de pagos",
  "component": "payments-gateway",
  "severity": "P0",
  "created_at": "2026-11-24T10:15:00+00:00",
  "status": "OPEN",
  "resolved_at": null,
  "recommended_team": "Backend-Core",
  "duplicate_group_key": "payments-gateway:http-502-outage",
  "rationale": "Fallo HTTP 502 en servicio crítico de pagos: P0 preventivo; alcance global por confirmar.",
  "consistency_ratio": 1.0,
  "is_duplicate": false,
  "duplicate_of": []
}
```

Los valores de `component`, `severity`, `recommended_team`, `duplicate_group_key` y `rationale` reproducen la clasificación real del motor para `raw_text` = `HTTP 502 Bad Gateway en pasarela de pagos`. `is_duplicate` es booleano y `duplicate_of` es una lista de identificadores. La clasificación completa se devuelve siempre; los campos antiguos sin valor aparecen como `null` y `[]` respectivamente. `raw_text` es solo entrada del triaje: no se persiste ni se devuelve. El esquema HTTP `IncidentCreatedResponse` mapea desde el DTO de aplicación `IncidentCreatedResult`.

### Respuesta de auditoría

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

`reference_time` se devuelve siempre, incluso cuando se omitió en la petición. Para resueltos, el cálculo usa `resolved_at`, conserva el incumplimiento histórico y nunca pide escalamiento (D04). El esquema HTTP `SLAEvaluationResponse` mapea desde `IncidentSLAResult`; `reference_time` no es un atributo de `SLAEvaluation`.

## REST

### E001 — Registrar un P0 válido

```powershell
$body = @{
  title    = "HTTP 502 en pasarela de pagos"
  raw_text = "HTTP 502 Bad Gateway en pasarela de pagos"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/incidents" `
  -Method Post -ContentType "application/json" -Body $body
```

Respuesta: `201 Created` con la estructura de alta, ID autogenerado `INC-HEX8`, `created_at` local y `status: "OPEN"`, sin `raw_text`. Si existe un equivalente abierto, se guarda igualmente con 201 y `is_duplicate: true`; no se usa 409.

### E014 — Registrar un P2 determinista

Se usa un identificador distinto del P0 anterior (H06) y fecha explícita naive; la referencia de la auditoría también será naive.

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

Respuesta: `201 Created`, con incidente P2, `created_at` respetado y `is_duplicate: false` si no hay candidatos.

### E005/E006 — Consultar SLA del P2

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/incidents/INC-P2F4E6A8/sla?reference_time=2026-11-09T09:00:00" `
  -Method Get
```

Respuesta: `200 OK` con `120/480/360`, `false`, `false` y `reference_time` igual al enviado.

Si se omite `reference_time`, se usa un instante actual compatible con la convención temporal del incidente almacenado.

### Errores REST

| Situación | Respuesta | Detalle |
|---|---|---|
| `title` o `raw_text` vacío o solo espacios | 422 | Validación de campos obligatorios. |
| `incident_id` existente, incluso en concurrencia | 422 | El registro original permanece sin cambios; no se usa HTTP 409. |
| `status` RESOLVED o desconocido | 422 | No se persiste el incidente. |
| ID inexistente en auditoría | 404 | El incidente consultado no existe. |
| `reference_time` inválido, anterior a `created_at`, naive/aware mezclado u offset distinto en P2/P3 | 422 | No se devuelve cálculo engañoso. |
| Almacenamiento efímero por operación | 503 | No se guarda ni se devuelve éxito falso. |

HTTP 409 no forma parte del contrato. Un equivalente abierto es un alta válida: se guarda con 201, `is_duplicate: true` y `duplicate_of` con los candidatos.

Ejemplo de error 503:

```json
{
  "detail": "La configuración de almacenamiento no conserva datos entre operaciones; defina DATABASE_URL con un archivo SQLite."
}
```

## CLI

### E001 — Registrar un P0 válido

```powershell
$env:DATABASE_URL = "sqlite:///incidentops.db"
uv run python -m src.adapters.inbound.cli create `
  --title "HTTP 502 en pasarela de pagos" `
  --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"
```

Salida: código `0` y el mismo JSON de alta que REST, con ID autogenerado.

### E014 — Registrar el mismo P2 en almacenamiento aislado equivalente

```powershell
$env:DATABASE_URL = "sqlite:///incidentops-cli-parity.db"
uv run python -m src.adapters.inbound.cli create `
  --title "Latencia alta en API pública" `
  --raw-text "Latencia alta sostenida en la API pública sin pérdida de servicio" `
  --incident-id "INC-P2F4E6A8" `
  --created-at "2026-11-06T17:00:00"
```

Con el mismo `incident_id` y `created_at` que el ejemplo REST, la salida coincide en identificador, fecha, clasificación, `is_duplicate` y `duplicate_of` (H08).

### E005/E006 — Auditar el mismo incidente del archivo compartido

```powershell
$env:DATABASE_URL = "sqlite:///incidentops.db"
uv run python -m src.adapters.inbound.cli sla `
  --incident-id "INC-P2F4E6A8" `
  --reference-time "2026-11-09T09:00:00"
```

Salida: código `0` y el mismo JSON de auditoría que REST, incluido `reference_time`.

### E015 — Almacenamiento efímero

```powershell
$env:DATABASE_URL = "sqlite:///:memory:"
uv run python -m src.adapters.inbound.cli create `
  --title "HTTP 502 en pasarela de pagos" `
  --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"
$LASTEXITCODE
```

Salida: código `1`, sin ID ni respuesta de éxito. El equivalente REST responde 503.

## Reglas comunes de equivalencia

- La creación se compara con almacenamientos aislados equivalentes y con `incident_id`/`created_at` explícitos; el estado por defecto es OPEN. `raw_text` únicamente alimenta el triaje y no se compara como campo de respuesta ni se persiste.
- Los duplicados equivalentes se registran con 201 y aviso; los IDs repetidos se rechazan con 422 sin sobrescritura. No se usa HTTP 409.
- La auditoría se compara con el mismo archivo SQLite, el mismo incidente y el mismo `reference_time` explícito.
- La clasificación completa, `is_duplicate`, `duplicate_of` y `reference_time` forman parte del JSON observable; no se comparan mensajes de excepción internos.
- Los ejemplos P0 y P2 usan identificadores diferentes para no mezclar un alta con una auditoría distinta (H06).
- La zona local por defecto depende del entorno; la paridad determinista usa fechas explícitas.

## Trazabilidad BDD

| Escenario | Contrato que lo evidencia |
|---|---|
| E001 | Alta P0 REST/CLI con almacenamiento persistente. |
| E002 | 422/código 1 por campos vacíos. |
| E003 | Alta 201 con `is_duplicate: true` y `duplicate_of` con OPEN/IN_PROGRESS/ESCALATION_REQUIRED; no 409. |
| E004 | Sin aviso para RESOLVED o sin coincidencia. |
| E005 | Campos completos de auditoría y `reference_time` efectivo. |
| E006 | Ejemplo P2 con 120/480/360, `false`, `false`. |
| E007 | Resuelto con validación temporal y cálculo hasta `resolved_at`. |
| E008 | Misma auditoría REST/CLI sobre el mismo archivo SQLite. |
| E009 | 404/código 1 para ID inexistente. |
| E010 | 422/código 1 para referencia inválida o anterior a creación. |
| E011 | 422/código 1 por ID existente, incluida concurrencia; sin sobrescritura ni HTTP 409. |
| E012 | 422/código 1 para fechas incompatibles. |
| E013 | 422/código 1 para RESOLVED o estado desconocido. |
| E014 | Misma creación en almacenamientos aislados equivalentes. |
| E015 | 503/código 1 con almacenamiento efímero, sin falso éxito. |
