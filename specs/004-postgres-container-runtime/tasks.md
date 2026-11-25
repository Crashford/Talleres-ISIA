---

description: "Task list for H004 — Persistencia dedicada y runtime en contenedores"
---

# Tasks: H004 — Persistencia dedicada y runtime en contenedores

**Input**: Design documents from `/specs/004-postgres-container-runtime/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD/RED-GREEN con BDD E001–E006 en `tests/test_spec_004_runtime_health.py`; el fallo RED y el resultado GREEN se registran antes de marcar tareas.

**Organization**: fases 1–2 son prerequisites; fases 3–5 agrupan US1, US2 y US3; fase 6 es verificación y evidencia.

**Branch**: `practica-guiada-sdd-semana-2` (conservar).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: solo archivos distintos y sin dependencias incompletas.
- **[Story]**: US1, US2 o US3 en las fases de historias.
- Incluir rutas exactas en cada descripción.
- Ninguna casilla se marca sin evidencia real.

## Path Conventions

- Proyecto único: `src/`, `tests/`, `evidence/` y archivos Compose en la raíz.
- Sin instalar dependencias: asumir `psycopg[binary]>=3.3.9` ya declarado en `pyproject.toml` y `uv.lock`.
- Sin ORM, sin drivers en dominio/aplicación y sin endpoints nuevos fuera de `/health`.
- Timestamps `TEXT` ISO 8601 en ambos adaptadores según `data-model.md`.

---

## Phase 1: Setup

**Purpose**: confirmar dependencia declarada y fronteras de imports antes de tocar código.

- [X] T001 [P] Verificar en `pyproject.toml` y `uv.lock` que `psycopg[binary]>=3.3.9` está declarado y que la rama activa sigue siendo `practica-guiada-sdd-semana-2`, sin ejecutar instalación
- [X] T002 [P] Confirmar en `pyproject.toml`, `src/domain/ruff.toml`, `src/application/ruff.toml` y `src/adapters/inbound/ruff.toml` que las reglas TID siguen prohibiendo imports de `psycopg` fuera de `src/adapters/outbound/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: contrato de salud y dobles compartidos por las tres historias.

**CRITICAL**: ninguna historia puede comenzar hasta completar esta fase.

- [X] T003 [P] Añadir `IncidentService.check_health()` en `src/application/services.py`, delegando en `IncidentRepositoryPort.check_health()` sin importar `psycopg`, `sqlite3` ni `DATABASE_URL`
- [X] T004 [P] Añadir `HealthResponse` en `src/adapters/inbound/api/schemas.py` con `Resultado de salud.status` y `Resultado de salud.database` según `data-model.md`, sin campo `detail`
- [X] T005 [P] Preparar en `tests/test_spec_004_runtime_health.py` los dobles reutilizables del puerto y de `psycopg.connect` con `TestClient` y `CliRunner` aislados, sin aserciones de comportamiento aún

**Checkpoint**: foundations listas; las historias pueden iniciarse en orden de prioridad.

---

## Phase 3: User Story 1 - Chequeo real de salud (Priority: P1) MVP

**Goal**: confirmar servicio y base accesibles desde REST y CLI con un `SELECT 1` real.

**Independent Test**: invocar `GET /health` y el comando `health` con un puerto que devuelve `True` y después con uno que devuelve `False`, comparando cuerpo, HTTP y código de salida.

### Tests for User Story 1

> Ejecutar primero y confirmar que fallan antes de la implementación.

- [X] T006 [US1] Escribir `test_bdd_e001_health_connected` en `tests/test_spec_004_runtime_health.py` verificando HTTP 200 y JSON `{"status":"ok","database":"connected"}` en `GET /health` y código 0 con el mismo JSON en el comando `health`
- [X] T007 [US1] Escribir `test_bdd_e002_health_unavailable` en `tests/test_spec_004_runtime_health.py` verificando HTTP 503 y JSON `{"status":"error","database":"unavailable"}` y código 1 sin fallback de almacenamiento

### Implementation for User Story 1

- [X] T008 [P] [US1] Implementar `GET /health` en `src/adapters/inbound/api/app.py` usando `HealthResponse` y `JSONResponse` para 200/503 con los cuerpos exactos de `data-model.md`
- [X] T009 [P] [US1] Implementar el comando `health` en `src/adapters/inbound/cli.py` imprimiendo el mismo JSON en `stdout` y devolviendo `0`/`1` según `check_health()`

**Checkpoint**: US1 es funcional y verificable de forma independiente con E001/E002.

---

## Phase 4: User Story 2 - Selección transparente del adaptador (Priority: P1)

**Goal**: ejecutar la misma aplicación con SQLite o PostgreSQL según configuración, sin ramas de negocio.

**Independent Test**: ejecutar el chequeo de salud con `DATABASE_URL` ausente, con `sqlite:///...` y con `postgresql://...`, verificando qué almacenamiento recibe `SELECT 1`.

### Tests for User Story 2

> Ejecutar primero y confirmar que fallan antes de la implementación.

- [X] T010 [US2] Escribir `test_bdd_e003_default_sqlite_memory` y `test_bdd_e004_sqlite_url` en `tests/test_spec_004_runtime_health.py` confirmando `sqlite:///:memory:` sin variable y el archivo indicado con prefijo `sqlite:///`
- [X] T011 [US2] Escribir `test_bdd_e005_postgres_url` en `tests/test_spec_004_runtime_health.py` confirmando selección PostgreSQL, `dict_row`, `SELECT 1` parametrizado y serialización ISO 8601 en `incidents.created_at` y `incidents.resolved_at` según `data-model.md`

### Implementation for User Story 2

- [X] T012 [P] [US2] Extender `src/adapters/outbound/factory.py` para seleccionar por `Configuración de persistencia.DATABASE_URL` de `data-model.md`: ausente → `sqlite:///:memory:`, `sqlite:///` → SQLite, `postgresql://` → PostgreSQL, otro esquema → `ValueError`
- [X] T013 [P] [US2] Crear en `src/adapters/outbound/postgres_repository.py` el esquema y los índices de `data-model.md` (`incidents.incident_id`, `incidents.title`, `incidents.component`, `incidents.severity`, `incidents.status`, `incidents.created_at`, `incidents.resolved_at`, `incidents.recommended_team`, `incidents.duplicate_group_key`, `sla_policies.severity`, `sla_policies.max_resolution_minutes`, `sla_policies.operates_24x7`), respetando `NOT NULL`/nullable, y el `check_health()` con `SELECT 1`
- [X] T014 [US2] Implementar en `src/adapters/outbound/postgres_repository.py` los métodos del puerto usando SQL con `%s`, `incidents.incident_id` con `DO NOTHING`, `sla_policies.severity` con `DO UPDATE` solo en sembrado, e `incidents.created_at`/`incidents.resolved_at` como `TEXT` ISO 8601 según `data-model.md`
- [X] T015 [US2] Verificar la regresión H003 en `tests/test_spec_003_lifecycle_sla.py` y `src/adapters/outbound/sqlite_repository.py`, conservando 88 pruebas y 10 subpruebas sin cambios de reglas de triaje/SLA

**Checkpoint**: US2 es funcional y verificable con E003–E005 sin romper H001–H003.

---

## Phase 5: User Story 3 - Arranque orquestado y reproducible (Priority: P2)

**Goal**: levantar la pila con la base lista antes que la API y con salud basada en conectividad real.

**Independent Test**: revisar la composición y, cuando Docker esté disponible, levantarla dos veces desde cero comprobando imagen, volumen, readiness de `db`, dependencia de `api` y healthcheck `/health`; si no está disponible, registrar la limitación sin afirmar SC-004.

### Tests for User Story 3

> Ejecutar primero y confirmar que falla antes de la implementación.

- [X] T016 [US3] Escribir `test_bdd_e006_compose_structure` en `tests/test_spec_004_runtime_health.py` leyendo `Dockerfile`, `.dockerignore` y `docker-compose.yml` y afirmando imagen base, servicio `db`, volumen, `pg_isready`, `depends_on: service_healthy` y healthcheck `/health`

### Implementation for User Story 3

- [X] T017 [P] [US3] Crear `Dockerfile` con `python:3.12-slim` e instalación/configuración de `uv`, y `.dockerignore` excluyendo `.git/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` y `evidence/`
- [X] T018 [P] [US3] Crear `docker-compose.yml` con servicios `db` y `api` según `data-model.md`: `postgres:16-alpine`, volumen persistente, healthcheck `pg_isready`, `DATABASE_URL` hacia `db`, `depends_on: service_healthy` y healthcheck de `api` sobre `/health` vía `urllib.request`
- [X] T019 [US3] Validar la estructura de `docker-compose.yml` y `Dockerfile` con la comprobación estática descrita en `specs/004-postgres-container-runtime/quickstart.md` y, cuando Docker esté disponible, ejecutar dos arranques consecutivos desde cero (`docker compose up --build`, `docker compose ps`) verificando que `db` alcanza `healthy` antes de `api` y que `/health` solo pasa con conectividad real; si Docker no está disponible, registrar la limitación en `evidence/H004-verify.md` sin afirmar SC-004

**Checkpoint**: US3 quedó evidenciado con dos arranques consecutivos, salud real de US1/US2 y cierre documentado en `evidence/H004-verify.md`; la limitación inicial sin Docker quedó registrada históricamente en el mismo archivo.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: regresión completa, evidencia honesta y paridad de contratos.

- [X] T020 [P] Ejecutar `uv run ruff check src/` y `uv run pytest -v` y confirmar en `specs/004-postgres-container-runtime/quickstart.md` que se conservan 88 pruebas y 10 subpruebas previas
- [X] T021 Registrar en `evidence/H004-verify.md` los resultados reales de RED/GREEN, Ruff, pytest, validación estructural de Compose y, si ocurrió, los dos arranques de SC-004; si Docker no estuvo disponible, documentar explícitamente la limitación sin afirmar el criterio
- [X] T022 [P] Revisar `specs/004-postgres-container-runtime/contracts/health.md` frente a `src/adapters/inbound/api/app.py` y `src/adapters/inbound/cli.py`, confirmando en `src/domain/ruff.toml` y `src/application/ruff.toml` que no se añadieron dependencias de infraestructura

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias; solo verificación.
- **Foundational (Phase 2)**: depende de Setup; bloquea las tres historias.
- **User Stories (Phase 3+)**: dependen de Foundational; ejecutar en orden P1 → P1 → P2 si hay una sola persona.
- **Polish (Phase 6)**: depende de las historias incluidas en el incremento.

### User Story Dependencies

- **US1 (P1)**: puede iniciar tras Foundational; no depende de US2 ni US3.
- **US2 (P1)**: puede iniciar tras Foundational; reutiliza el contrato REST/CLI de US1 para paridad completa, pero es testeable de forma aislada en fábrica/repositorio.
- **US3 (P2)**: la validación estructural es independiente; la evidencia de dos arranques con salud real requiere US1, US2 y Docker disponible.

### Within Each User Story

- Tests primero: confirmar RED antes de implementar y GREEN después.
- En `tests/test_spec_004_runtime_health.py`, T006/T007, T010/T011 y T016 son secuenciales por compartir archivo.
- Fábrica y esquema PostgreSQL pueden avanzar en paralelo; los métodos CRUD del mismo repositorio van después del esquema.
- Cada historia termina en su checkpoint antes de pasar a la siguiente prioridad.

### Parallel Opportunities

- Setup: T001 y T002.
- Foundational: T003, T004 y T005.
- US1: T008 y T009 tras T006/T007.
- US2: T012 y T013 tras T010/T011; T014 después de T013.
- US3: T017 y T018 tras T016; T019 depende de T017/T018 y ejecuta la evidencia de arranque solo con Docker disponible.
- Polish: T020 y T022; T021 después de recibir resultados reales.

---

## Parallel Example: User Story 1

```bash
# Secuencial por el mismo archivo de pruebas:
Task: "T006 [US1] Escribir test_bdd_e001_health_connected en tests/test_spec_004_runtime_health.py"
Task: "T007 [US1] Escribir test_bdd_e002_health_unavailable en tests/test_spec_004_runtime_health.py"

# En paralelo tras RED:
Task: "T008 [P] [US1] Implementar GET /health en src/adapters/inbound/api/app.py"
Task: "T009 [P] [US1] Implementar comando health en src/adapters/inbound/cli.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Completar Phase 1 y Phase 2.
2. Completar Phase 3 (US1).
3. Validar E001/E002 de forma aislada.
4. El despliegue PostgreSQL queda para US2; no incluirlo en el MVP de salud.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → salud REST/CLI real → MVP.
3. US2 → selección SQLite/PostgreSQL y regresión H003.
4. US3 → Compose con orden de readiness, healthcheck real y evidencia de arranque cuando Docker esté disponible.
5. Polish → Ruff, pytest completo, evidencia y paridad.

### Parallel Team Strategy

1. Equipo completo: Setup + Foundational.
2. Desarrollador A: US1; Desarrollador B: US2; Desarrollador C: US3.
3. Integrar solo en checkpoints y conservar regresiones H001–H003.

---

## Notes

- `[P]` significa archivos distintos y sin dependencias incompletas.
- `[Story]` permite trazabilidad hacia E001–E006.
- Todas las tareas usan el formato `- [ ] [TaskID] [P?] [Story?] Descripción con ruta exacta`.
- No marcar casillas sin evidencia real de RED/GREEN o verificación.
- No instalar dependencias ni cambiar de rama salvo solicitud explícita; Docker solo para la evidencia de SC-004 cuando esté disponible.
- No ejecutar commit salvo solicitud explícita.
