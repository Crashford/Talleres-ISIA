# Implementation Plan: H003 — Ciclo de vida, duplicados y SLA

**Branch**: `practica-guiada-sdd-semana-2` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Status**: curado tras revisión humana; decisiones D01–D05, correcciones H06–H08 y curaduría Analyze-A1–A7 aprobadas; `tasks.md` curado y aprobado; pendiente de autorización para Build, sin implementación ni ejecución de pruebas.

> `setup-plan.sh` informó `BRANCH=003-incident-lifecycle-sla` porque deriva el identificador de `.specify/feature.json` (`common.sh:217-224`). La rama Git verificada es `practica-guiada-sdd-semana-2` y permanece activa; no se crea ni cambia ninguna rama.

## Summary

Registrar incidentes de forma persistente y atómica, avisar de equivalentes abiertos y auditar SLA desde REST y CLI mediante un único `IncidentService`. Se reutilizan triaje y SLA de H001/H002, se centraliza la normalización temporal en el dominio con offset local por defecto, y se amplía SQLite con migración compatible, índice de duplicados, inserción sin sobrescritura y rechazo explícito de almacenamiento efímero en el alta.

## Technical Context

- **Language/Version**: Python >=3.10, gestionado con `uv`.
- **Primary Dependencies**: FastAPI, Pydantic v2 y Typer; Ruff, pytest y httpx para calidad. Sin dependencias nuevas, PostgreSQL ni Docker.
- **Storage**: SQLite3 estándar vía `DATABASE_URL`; valor por defecto inalterado `sqlite:///:memory:`. El alta exige almacenamiento que conserve datos entre operaciones; un archivo SQLite explícito es la configuración documentada para H003.
- **Testing**: pytest con `TestClient`, `CliRunner`, SQLite aislado por `tmp_path` y Ruff jerárquico. Línea base: 51 pruebas y 10 subpruebas (`evidence/H002-verificacion.md:15,18`).
- **Target Platform**: backend y terminal multiplataforma; mismo comportamiento en REST y CLI.
- **Project Type**: proyecto Python único con adaptadores primarios REST/CLI y adaptador secundario SQLite.
- **Performance Goals**: búsqueda de duplicados filtrada en SQL con índice compuesto; sin N+1 nuevo. No se inventa umbral de latencia.
- **Constraints**: Constitución 1.0.0, ADR-001/002/003, skills `hexagonal-architecture` y `bdd-acceptance`; sin transiciones de estado, notificaciones, festivos, H004 ni cambios de motor.
- **Scale/Scope**: 15 escenarios E001–E015, FR-001–FR-015 y SC-001–SC-006; regresiones H001/H002 conservadas.
- **Clarifications**: A1–A3, T1–T6, Q1–Q3, curaduría D01–D05/H06–H08 y Analyze-A1–A7 incorporadas en [spec.md](spec.md) y [research.md](research.md); no quedan decisiones pendientes de aprobación.

## Constitution Check

*GATE: superado antes de Phase 0 y revalidado tras la curaduría de Phase 1.*

| Principio | Verificación | Resultado |
|---|---|---|
| I — Dominio determinista único | Triaje y SLA se reutilizan; la normalización temporal, incluido `datetime.now().astimezone()`, vive en `sla_calculator.py`; `TeamName` deriva del `Literal` existente. | PASS |
| II — Hexagonal estricta | REST/CLI delegan en `IncidentService`; el puerto sigue en aplicación; la capacidad de persistencia se expone sin filtrar `DATABASE_URL`, SQLite ni drivers al núcleo; Ruff TID251/TID252 se mantiene. | PASS |
| III — SLA y estados | ADR-002 se conserva; resueltos calculan hasta `resolved_at` con validación temporal y sin reconstrucción; `list_active_incidents` sigue con OPEN/IN_PROGRESS; el alta admite tres estados iniciales y rechaza RESOLVED/desconocidos. | PASS |
| IV — Paridad y aceptación verificable | Un caso de uso por operación; 15 escenarios BDD; creación con almacenamientos aislados equivalentes y consultas con el mismo archivo; JSON completo y `reference_time` explícito. | PASS |
| V — Calidad y simplicidad | Sin dependencias nuevas; migración aditiva, índice solicitado e inserción atómica; verificación prevista con `uv run ruff check src/` y `uv run pytest -v`. | PASS |

**Gate**: PASS. No hay violaciones que justificar en *Complexity Tracking*.

## Project Structure

```text
specs/003-incident-lifecycle-sla/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/incidents.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md              # Curado y aprobado por /speckit.tasks
src/
├── domain/
│   ├── models.py         # Ampliar Incident y alias TeamName
│   ├── sla_calculator.py # Centralizar normalización temporal
│   ├── triage_rules.py   # Reutilizar sin cambiar reglas
│   └── ruff.toml
├── application/
│   ├── dtos.py           # IncidentCreatedResult, IncidentSLAResult (dataclasses)
│   ├── ports.py          # save -> bool y supports_persistent_writes
│   ├── services.py       # create_incident, evaluate_incident_sla, errores
│   └── ruff.toml
├── adapters/
│   ├── inbound/
│   │   ├── api/{app,schemas}.py
│   │   ├── cli.py
│   │   └── ruff.toml
│   └── outbound/
│       ├── factory.py
│       └── sqlite_repository.py
tests/
├── conftest.py
├── test_spec_001_triage.py
├── test_spec_002_summary.py
└── test_spec_003_lifecycle_sla.py  # Destino de E001–E015
```

**Structure Decision**: conservar el proyecto único y la arquitectura hexagonal existente. No se crean servicios paralelos, nuevos paquetes, motor de base de datos ni adaptadores primarios adicionales.

## Diseño técnico

1. **Dominio**: en `src/domain/models.py`, crear `TeamName` a partir del `Literal` actual y ampliar `Incident` al final del dataclass con `recommended_team: Optional[TeamName] = None` y `duplicate_group_key: Optional[str] = None`. En `src/domain/sla_calculator.py`, centralizar lectura ISO 8601, instante actual local (`datetime.now().astimezone()` si `created_at` se omite) y validación temporal; `evaluate_sla_status` conserva ADR-002. Las fechas explícitas se respetan; la zona local depende del entorno y la paridad determinista usa fechas y referencias explícitas.
2. **Aplicación**: en `src/application/dtos.py`, definir `IncidentCreatedResult` e `IncidentSLAResult` como dataclasses sin Pydantic, con tipos del dominio cuando corresponda. En `src/application/services.py`, añadir `IncidentNotFoundError` y `PersistentStorageUnavailableError`, además de `create_incident` y `evaluate_incident_sla`. `create_incident` recibe `title` y `raw_text` como entrada, valida D02/D03, verifica la capacidad de persistencia, clasifica con el triaje vigente, construye el `Incident` sin `raw_text`, guarda, consulta duplicados y devuelve `IncidentCreatedResult`. Un ID existente produce 422/código 1 sin sobrescritura; no se usa HTTP 409. `evaluate_incident_sla` usa `get_incident`, aplica la resolución temporal centralizada (D04) y devuelve `IncidentSLAResult` con el `reference_time` efectivo sin extender `SLAEvaluation`.
3. **Puerto y concurrencia (D01/D05)**: mantener `IncidentRepositoryPort` con ajustes mínimos: `save_incident(...) -> bool` mediante `INSERT ... ON CONFLICT(incident_id) DO NOTHING`; `supports_persistent_writes() -> bool`; `get_incident` hidrata campos nuevos; `find_open_duplicates` incluye ESCALATION_REQUIRED; `list_active_incidents` queda intacto. No se hace comprobación previa seguida de escritura. La aplicación traduce `False` a `ValidationError` y la falta de persistencia a `PersistentStorageUnavailableError` (503/código 1).
4. **SQLite**: en `src/adapters/outbound/sqlite_repository.py`, conservar el esquema actual, añadir `recommended_team TEXT` si falta, crear `idx_incidents_dup_key (duplicate_group_key, status)` con `IF NOT EXISTS`, adaptar `_to_incident`, `save_incident`, `get_incident`, `find_open_duplicates` y la capacidad de persistencia (`:memory:` = efímera). No se backfillean filas antiguas ni se altera `idx_incidents_component_status`.
5. **Adaptadores primarios**: en `schemas.py`, añadir los esquemas HTTP `CreateIncidentRequest`, `IncidentCreatedResponse` y `SLAEvaluationResponse`, mapeando desde/hacia los DTOs de aplicación; `raw_text` solo existe en la petición de alta y no se devuelve. En `app.py`, registrar `POST /api/v1/incidents` con 201/422/503 y `GET /api/v1/incidents/{incident_id}/sla` con 200/404/422; un equivalente abierto se guarda con 201 y aviso, un ID existente se rechaza con 422 sin sobrescritura y no se usa 409. En `cli.py`, añadir `create` y `sla` con código 1 ante errores de aplicación y código 0 con el mismo JSON. Los ejemplos P0 y P2 usan IDs distintos y el caso P2 reproduce los cinco valores exigidos (H06).
6. **Persistencia compartida (D05/H08)**: conservar `factory.py`, el default en memoria y el ciclo de conexión por operación. El alta sobre almacenamiento efímero se rechaza sin falso éxito; las pruebas de creación usan almacenamientos aislados equivalentes y las de consulta REST/CLI usan el mismo archivo SQLite. Ver [quickstart.md](quickstart.md).
7. **Pruebas**: crear `tests/test_spec_003_lifecycle_sla.py` con una función `test_bdd_*` por escenario E001–E015, almacenamiento aislado, altas concurrentes sobre el mismo ID, JSON completo para paridad, `reference_time` fijo y sin replicar el algoritmo. H07 identifica regresiones H002 que pueden necesitar ajustes mínimos de fixtures; no se eliminan pruebas ni se debilitan aserciones.

### Cobertura BDD E001–E015

| Escenario | Función de aceptación | Foco observable |
|---|---|---|
| E001 | `test_bdd_e001_create_valid` | Alta válida con archivo SQLite; 201/JSON equivalente, ID, fecha local, clasificación y sin duplicado. |
| E002 | `test_bdd_e002_blank_input` | Título o texto vacío; 422 y código 1 sin persistir. |
| E003 | `test_bdd_e003_open_duplicate` | Coincidencia exacta en OPEN/IN_PROGRESS/ESCALATION_REQUIRED; 201 con `is_duplicate: true` y `duplicate_of` correcto; no 409. |
| E004 | `test_bdd_e004_no_duplicate` | Solo RESOLVED o sin coincidencia; sin aviso. |
| E005 | `test_bdd_e005_sla_audit` | `reference_time` efectivo y cinco valores de SLA por REST y CLI. |
| E006 | `test_bdd_e006_deterministic_p2` | P2 con ID propio: 120/480/360, `false`, `false`. |
| E007 | `test_bdd_e007_resolved_sla` | Resuelto: validación temporal, cálculo hasta `resolved_at`, sin escalamiento ni reconstrucción. |
| E008 | `test_bdd_e008_rest_cli_sla_parity` | Mismo archivo SQLite, incidente y referencia explícita; JSON idéntico. |
| E009 | `test_bdd_e009_missing_incident` | ID inexistente; 404 y código 1. |
| E010 | `test_bdd_e010_invalid_reference` | Formato inválido o anterior a creación; 422 y código 1. |
| E011 | `test_bdd_e011_duplicate_id` | ID repetido, incluidas altas concurrentes; 422/código 1, registro original intacto y sin HTTP 409. |
| E012 | `test_bdd_e012_incompatible_dates` | Mezcla naive/aware y offsets distintos en P2/P3; 422/código 1; referencia omitida compatible. |
| E013 | `test_bdd_e013_invalid_initial_status` | RESOLVED y estados desconocidos rechazados; sin persistencia. |
| E014 | `test_bdd_e014_create_parity` | Mismo ID/fecha en almacenamientos aislados equivalentes; respuestas equivalentes. |
| E015 | `test_bdd_e015_ephemeral_storage` | Alta con almacenamiento efímero; 503/código 1 sin falso éxito. |

### Verificación prevista en Build

```sh
export DATABASE_URL=sqlite:///incidentops.db
uv run ruff check src/
uv run pytest -v
uv run python -m src.adapters.inbound.cli create --title "Latencia alta en API pública" --raw-text "Latencia alta sostenida en la API pública sin pérdida de servicio" --incident-id INC-P2F4E6A8 --created-at "2026-11-06T17:00:00"
uv run python -m src.adapters.inbound.cli sla --incident-id INC-P2F4E6A8 --reference-time 2026-11-09T09:00:00
```

Criterio de evidencia: Ruff sin infracciones; 51 pruebas y 10 subpruebas de la línea base más 15 escenarios nuevos; evidencia real guardada en un archivo nuevo bajo `evidence/` solo después de ejecutar los comandos.

## Riesgos operativos

- D01 requiere demostrar concurrencia real y que el registro original no se modifica; las regresiones H002 no deben debilitarse (H07).
- D02 depende del offset local del entorno; por eso la paridad determinista usa fechas y referencias explícitas.
- D05 mantiene el default efímero: el rechazo 503/código 1 evita falsos éxitos, pero las operaciones persistentes requieren configurar un archivo SQLite.
- La centralización temporal toca una ruta usada por H002; la regresión completa es obligatoria antes de declarar terminado el hito.

## Complexity Tracking

Sin desviaciones de la Constitución que requieran justificación. No se añaden dependencias, motores, paquetes ni funcionalidades de H004.
