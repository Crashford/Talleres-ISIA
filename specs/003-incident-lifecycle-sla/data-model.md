# Data Model — H003: ciclo de vida, duplicados y SLA

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Estado**: curado con D01–D05, H06–H08 y Analyze-A1–A7

## Visión general

El modelo amplía el `Incident` existente sin romper H001/H002, centraliza la normalización temporal en el dominio y conserva un único puerto de persistencia. La configuración de almacenamiento permanece en el adaptador: si es efímera por operación, el alta falla con HTTP 503/código 1 antes de clasificar o persistir, sin falso éxito (D05).

## Matriz entidad → propósito → origen

| Entidad / tipo                                                                  | Propósito                                                                   | Origen                                                |
| ------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------- |
| `TeamName`                                                                      | Unión canónica de equipos derivada del `Literal` vigente.                   | `src/domain/models.py` (nuevo alias, sin nueva lista) |
| `Incident`                                                                      | Registro persistido con estado y campos de triaje/duplicados.               | `src/domain/models.py` (ampliar)                      |
| `TriageResult`                                                                  | Clasificación devuelta por el motor vigente.                                | `src/domain/triage_rules.py` (reutilizar)             |
| `SLAEvaluation`                                                                 | Cálculo observable del SLA en dominio, sin `reference_time`.                | `src/domain/sla_calculator.py` (reutilizar/extender)  |
| `IncidentCreatedResult` / `IncidentSLAResult`                                   | DTOs de aplicación devueltos por los casos de uso.                          | `src/application/dtos.py` (nuevo; dataclasses)        |
| `CreateIncidentRequest` / `IncidentCreatedResponse` / `SLAEvaluationResponse`   | Esquemas HTTP de entrada y salida.                                          | `src/adapters/inbound/api/schemas.py` (nuevos)        |
| `IncidentRepositoryPort`                                                        | Contrato de persistencia con inserción atómica y capacidad de persistencia. | `src/application/ports.py` (ajustar)                  |
| `ValidationError`, `IncidentNotFoundError`, `PersistentStorageUnavailableError` | Errores de aplicación traducidos a 422/404/503 y códigos CLI.               | `src/application/services.py`                         |

## Dominio

### `TeamName`

```python
TeamName = Literal["Backend-Core", "Platform-SRE", "Data-DBA", "Security-IAM"]
```

Se deriva del `Literal` actual de `recommended_team` en `src/domain/models.py`, que `triage_rules.py` aplica mediante `COMPONENT_TEAMS`. No se introduce una enumeración paralela.

### `Incident` (`src/domain/models.py`)

| Campo                 | Tipo                 | Regla                                                                                                                                                                                |
| --------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `incident_id`         | `str`                | Generado como `INC-HEX8` si se omite; si se proporciona, debe ser texto no vacío. Un ID existente se rechaza con 422/código 1 y sin sobrescribir, incluso en concurrencia (D01/D03). |
| `title`               | `str`                | Obligatorio, no vacío ni solo espacios.                                                                                                                                              |
| `component`           | `str`                | Procedente del triaje.                                                                                                                                                               |
| `severity`            | `str`                | P0–P3 procedente del triaje.                                                                                                                                                         |
| `created_at`          | `datetime`           | Si se omite en el alta, se usa `datetime.now().astimezone()` (offset local del entorno); las fechas explícitas se respetan (D02).                                                    |
| `status`              | `str`                | OPEN por defecto; inicialmente válidos OPEN, IN_PROGRESS y ESCALATION_REQUIRED; RESOLVED y desconocidos se rechazan en el alta (D03).                                                |
| `recommended_team`    | `Optional[TeamName]` | Derivado del triaje; por defecto `None` para registros antiguos.                                                                                                                     |
| `duplicate_group_key` | `Optional[str]`      | Derivado del triaje; por defecto `None` para registros antiguos.                                                                                                                     |
| `resolved_at`         | `Optional[datetime]` | Solo en incidentes resueltos ya existentes; no se acepta en el alta ni implica transición de estado.                                                                                 |

Los campos nuevos se añaden al final del dataclass con valores por defecto para conservar los constructores posicionales de H002 (H07). El dataclass no conoce SQLite, `DATABASE_URL` ni códigos HTTP. `raw_text` no es un atributo de `Incident`: se usa solo como entrada del triaje y no se persiste ni se devuelve.

### `TriageResult`

Se reutiliza `classify_incident_report` sin duplicar reglas. Su resultado se propaga sin alterarlo:

| Campo de `TriageResult` | Destino canónico                                                                                                                 |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `severity`              | `Incident.severity` → `IncidentCreatedResult.severity` → `IncidentCreatedResponse.severity`                                      |
| `component`             | `Incident.component` → `IncidentCreatedResult.component` → `IncidentCreatedResponse.component`                                   |
| `rationale`             | `IncidentCreatedResult.rationale` → `IncidentCreatedResponse.rationale`; no se persiste                                          |
| `consistency_ratio`     | `IncidentCreatedResult.consistency_ratio` → `IncidentCreatedResponse.consistency_ratio`; no se persiste                          |
| `recommended_team`      | `Incident.recommended_team` (persistido) → `IncidentCreatedResult.recommended_team` → `IncidentCreatedResponse.recommended_team` |
| `duplicate_group_key`   | `Incident.duplicate_group_key` (persistido) y `find_open_duplicates`; se expone también en el resultado y la respuesta del alta  |

### `SLAEvaluation` (`src/domain/sla_calculator.py`)

Se mantiene sin nuevos atributos: `reference_time` no pertenece al dominio. Se expone en `IncidentSLAResult` y en el esquema HTTP `SLAEvaluationResponse`.

| Campo                 | Regla                                                                                                                                                                            |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `elapsed_minutes`     | Minutos completos entre `created_at` y el fin efectivo del cómputo.                                                                                                              |
| `allowed_minutes`     | Política vigente del dominio: 60 para P0 y 240 para P1, ambos 24/7; 480 para P2 y 1440 para P3, ambos en jornada hábil de lunes a viernes [08:00, 18:00) sin festivos (ADR-002). |
| `remaining_minutes`   | Diferencia con `allowed_minutes`; no negativa cuando aún no hay incumplimiento.                                                                                                  |
| `is_breached`         | `True` solo si los minutos completos exceden el límite; monitorización sin escalamiento no equivale a incumplimiento.                                                            |
| `requires_escalation` | `True` desde el 75% exacto del tiempo permitido y tras el vencimiento mientras no se resuelva; `False` para resueltos (D04).                                                     |

### Convenciones temporales (D02/D04)

- La conversión de cadenas ISO 8601 y la resolución del instante actual viven en `sla_calculator.py`; adaptadores y servicios no reparsen fechas por su cuenta.
- `created_at` omitido usa `datetime.now().astimezone()`. La zona local depende del entorno; por eso E008/E014 usan fechas y referencias explícitas.
- Se rechazan: formato inválido, `reference_time < created_at`, mezcla naive/aware en cualquier orden y, para P2/P3, offsets distintos entre `created_at` y `reference_time`.
- Para incidentes resueltos, reference_time debe ser igual o posterior a created_at y respetar las convenciones temporales del ADR-002. El cálculo utiliza resolved_at, conserva el incumplimiento histórico y no solicita escalamiento. La referencia puede ser anterior o posterior a la resolución; la consulta no reconstruye estados históricos.
- No hay festivos, zonas múltiples ni DST dentro del tramo; la política no se modifica.

## Aplicación

### `IncidentRepositoryPort` (D01/D05)

| Método                                                                          | Contrato                                                                                                                                         |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `save_incident(incident: Incident) -> bool`                                     | Inserción atómica `INSERT ... ON CONFLICT(incident_id) DO NOTHING`. Devuelve `True` si insertó y `False` si el ID ya existía; nunca sobrescribe. |
| `supports_persistent_writes() -> bool`                                          | Indica si la configuración conserva datos entre operaciones. Es una capacidad del adaptador, no una regla de negocio.                            |
| `get_incident(incident_id: str) -> Optional[Incident]`                          | Devuelve el incidente hidratado, incluidos campos nuevos.                                                                                        |
| `find_open_duplicates(duplicate_group_key: str, incident_id: str) -> list[str]` | Devuelve IDs de OPEN, IN_PROGRESS y ESCALATION_REQUIRED con la misma clave exacta, excluido el propio.                                           |
| `list_active_incidents()`                                                       | Sin cambios: solo OPEN e IN_PROGRESS para el resumen H002.                                                                                       |

No se añade un método previo de existencia: la comprobación y la inserción forman una sola operación para evitar carreras.

### Servicios y errores

- `create_incident(...)`: recibe `title` y `raw_text` como entrada del caso de uso; valida D02/D03, consulta `supports_persistent_writes()`, clasifica con `raw_text`, construye el `Incident` sin ese campo, guarda y calcula duplicados. Si `save_incident` devuelve `False`, lanza `ValidationError` (422/código 1, sin HTTP 409). Si no hay persistencia, lanza `PersistentStorageUnavailableError` (503/código 1). Devuelve `IncidentCreatedResult`.
- `evaluate_incident_sla(...)`: obtiene el incidente, valida/normaliza `reference_time`, calcula con `evaluate_sla_status` y devuelve `IncidentSLAResult` con el `reference_time` efectivo; `SLAEvaluation` no se extiende.
- `ValidationError`: 422/código 1; cubre campos vacíos, ID existente sin sobrescritura, `status` RESOLVED/desconocido y fechas inválidas o incompatibles. No se usa HTTP 409.
- `IncidentNotFoundError`: 404/código 1.
- `PersistentStorageUnavailableError`: 503/código 1; sin persistencia ni respuesta de éxito.

## DTOs de aplicación (`src/application/dtos.py`)

Dataclasses independientes de Pydantic y de los esquemas HTTP. Usan tipos del dominio (`datetime`, `TeamName`, `IncidentStatus`) cuando corresponde; los adaptadores solo los mapean.

### `IncidentCreatedResult`

| Campo                 | Tipo                 | Origen                           |
| --------------------- | -------------------- | -------------------------------- |
| `incident_id`         | `str`                | `Incident.incident_id`           |
| `title`               | `str`                | `Incident.title`                 |
| `component`           | `str`                | `TriageResult.component`         |
| `severity`            | `str`                | `TriageResult.severity`          |
| `created_at`          | `datetime`           | `Incident.created_at`            |
| `status`              | `str`                | `Incident.status`                |
| `resolved_at`         | `Optional[datetime]` | `Incident.resolved_at`           |
| `recommended_team`    | `Optional[TeamName]` | `Incident.recommended_team`      |
| `duplicate_group_key` | `Optional[str]`      | `Incident.duplicate_group_key`   |
| `rationale`           | `str`                | `TriageResult.rationale`         |
| `consistency_ratio`   | `float`              | `TriageResult.consistency_ratio` |
| `is_duplicate`        | `bool`               | Aviso calculado en aplicación    |
| `duplicate_of`        | `list[str]`          | `find_open_duplicates`           |

No incluye `raw_text`.

### `IncidentSLAResult`

| Campo                 | Tipo       | Origen                                         |
| --------------------- | ---------- | ---------------------------------------------- |
| `incident_id`         | `str`      | `Incident.incident_id`                         |
| `reference_time`      | `datetime` | Referencia efectiva validada/normalizada (D04) |
| `elapsed_minutes`     | `int`      | `SLAEvaluation.elapsed_minutes`                |
| `allowed_minutes`     | `int`      | `SLAEvaluation.allowed_minutes`                |
| `remaining_minutes`   | `int`      | `SLAEvaluation.remaining_minutes`              |
| `is_breached`         | `bool`     | `SLAEvaluation.is_breached`                    |
| `requires_escalation` | `bool`     | `SLAEvaluation.requires_escalation`            |

`reference_time` vive aquí y en el esquema HTTP, no en `SLAEvaluation`.

## DTOs de interfaz (`src/adapters/inbound/api/schemas.py`)

### `CreateIncidentRequest`

| Campo         | Tipo                       | Obligatorio | Notas                                                                                |
| ------------- | -------------------------- | ----------- | ------------------------------------------------------------------------------------ |
| `title`       | `str` no vacío             | Sí          | Se rechaza si es solo espacios.                                                      |
| `raw_text`    | `str` no vacío             | Sí          | Único destino del texto entrante: alimenta el triaje; no se persiste ni se devuelve. |
| `incident_id` | `Optional[str]`            | No          | Autogenerado `INC-HEX8` si se omite; texto no vacío si se proporciona.               |
| `created_at`  | `Optional[datetime]`       | No          | Por defecto, `datetime.now().astimezone()`.                                          |
| `status`      | `Optional[IncidentStatus]` | No          | OPEN por defecto; OPEN/IN_PROGRESS/ESCALATION_REQUIRED permitidos.                   |

### `IncidentCreatedResponse`

Mapea desde `IncidentCreatedResult` con los mismos campos, sin `raw_text`. Debe ser equivalente entre REST y CLI; el orden de claves no es parte del contrato. Un equivalente abierto se registra con 201 y `is_duplicate: true`; un ID existente se rechaza con 422 sin sobrescritura. No se usa HTTP 409.

### `SLAEvaluationResponse`

Mapea desde `IncidentSLAResult`: `incident_id` y los seis campos de auditoría, incluido `reference_time`. No incluye estado reconstruido ni datos de otros incidentes.

## Persistencia SQLite (ADR-001)

### Esquema ampliado

```sql
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    component TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    recommended_team TEXT,
    duplicate_group_key TEXT
);

CREATE INDEX IF NOT EXISTS idx_incidents_component_status
    ON incidents(component, status);
CREATE INDEX IF NOT EXISTS idx_incidents_dup_key
    ON incidents(duplicate_group_key, status);
```

Migración: `ALTER TABLE incidents ADD COLUMN recommended_team TEXT` solo si la columna no existe. No se backfillean filas antiguas y se conserva el índice previo.

### Reglas del adaptador

- `find_open_duplicates` filtra `duplicate_group_key = ?`, `status IN ('OPEN', 'IN_PROGRESS', 'ESCALATION_REQUIRED')` e `incident_id <> ?`.
- `list_active_incidents` permanece con `status IN ('OPEN', 'IN_PROGRESS')`.
- `supports_persistent_writes()` devuelve `False` para configuraciones en memoria por operación; la fábrica mantiene `sqlite:///:memory:` como valor por defecto.
- Las pruebas de creación usan almacenamientos aislados equivalentes; las de auditoría usan el mismo archivo SQLite para REST y CLI (H08).

## Trazabilidad

| Requisito / escenario                                 | Elemento del modelo                                                                                                                                                                    |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E001/E002/E013/E014/E015, FR-001–FR-005/FR-014–FR-015 | `CreateIncidentRequest.raw_text` como entrada de triaje; `Incident` sin `raw_text`; `IncidentCreatedResult`; `save_incident`; `supports_persistent_writes`                             |
| E003/E004, FR-006/FR-007                              | `TriageResult.duplicate_group_key` → `Incident.duplicate_group_key`; `find_open_duplicates`; `IncidentCreatedResult.is_duplicate/duplicate_of`; `IncidentCreatedResponse`; 201, no 409 |
| E005–E012, FR-009–FR-012                              | `SLAEvaluation` sin `reference_time`; normalización temporal; `IncidentSLAResult.reference_time`; `SLAEvaluationResponse`                                                              |
| E011, FR-003                                          | Inserción atómica, `ValidationError` con 422/código 1 y registro original intacto; no 409                                                                                              |
| E014, FR-005/FR-013                                   | Los seis campos de `TriageResult` se reutilizan y se exponen en `IncidentCreatedResult`/`IncidentCreatedResponse` sin duplicar reglas                                                  |
| SC-006, H07                                           | Dataclass ampliada al final, migración aditiva y regresiones H002 sin cambios de aserción                                                                                              |
