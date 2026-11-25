---

description: "Task list for H003 — Ciclo de vida, duplicados y SLA"
---

# Tasks: H003 — Ciclo de vida, duplicados y SLA

**Input**: Design documents from `/specs/003-incident-lifecycle-sla/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD/RED-GREEN con cobertura BDD E001–E015; el fallo RED y el resultado GREEN se registran antes de marcar tareas.

**Organization**: fases 1–3 son prerequisites; fases 4–6 incluyen sus propios esquemas, rutas REST y comandos CLI por historia; fase 7 es verificación y evidencia.

**Branch**: `practica-guiada-sdd-semana-2` (conservar).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: solo archivos distintos y sin dependencias incompletas.
- **[Story]**: US1, US2 o US3 en las fases de historias.
- Incluir rutas exactas en cada descripción.
- Ninguna casilla se marca sin evidencia real.

## Path Conventions

- Proyecto único: `src/`, `tests/` y `evidence/` en la raíz.
- Sin dependencias nuevas, ORM, Docker, PostgreSQL ni funcionalidades de H004.
- `uv sync --locked` preserva el lockfile existente.

---

## Phase 1: Setup

**Purpose**: confirmar rama, entorno, línea base y contenedor de pruebas.

- [ ] T001 [P] Verificar que la rama activa sigue siendo `practica-guiada-sdd-semana-2` y que `AGENTS.md` y `.specify/feature.json` no tienen cambios ajenos a esta etapa
- [ ] T002 [P] Confirmar Python >=3.10 y ejecutar `uv sync --locked`, sin modificar `pyproject.toml` ni `uv.lock`
- [ ] T003 Ejecutar y registrar la línea base real con `uv run ruff check src/` y `uv run pytest -v` en `evidence/H003-baseline.md`, verificando 51 pruebas y 10 subpruebas según `evidence/H002-verificacion.md`
- [ ] T004 Crear fixtures aisladas (`tmp_path`, `TestClient`, `CliRunner`, `DATABASE_URL`) en `tests/test_spec_003_lifecycle_sla.py` y `tests/conftest.py`, sin aserciones de comportamiento aún

**Checkpoint**: entorno y línea base documentados.

---

## Phase 2: Foundational — Dominio y normalización temporal

**CRITICAL**: bloquea US1, US2 y US3.

- [ ] T005 Escribir y ejecutar las pruebas RED de normalización temporal en `tests/test_spec_003_lifecycle_sla.py` —default local aware, fechas explícitas, referencia omitida, mezcla naive/aware, offsets P2/P3 y rango de resuelto—; registrar el fallo esperado en `evidence/H003-red-green.md` y no implementar aún en `src/domain/sla_calculator.py`
- [ ] T006 Ampliar `TeamName` y `Incident` en `src/domain/models.py` aplicando `data-model.md` → `Incident.incident_id`, `Incident.title`, `Incident.component`, `Incident.severity`, `Incident.created_at`, `Incident.status`, `Incident.recommended_team`, `Incident.duplicate_group_key` e `Incident.resolved_at`; los únicos atributos nuevos son `recommended_team` y `duplicate_group_key`, añadidos al final para conservar constructores H002
- [ ] T007 Centralizar parsing ISO 8601, `datetime.now().astimezone()` y validación temporal en `src/domain/sla_calculator.py` según `data-model.md` → `Incident.created_at`, `Incident.resolved_at`, `SLAEvaluation.elapsed_minutes`, `SLAEvaluation.allowed_minutes`, `SLAEvaluation.remaining_minutes`, `SLAEvaluation.is_breached` y `SLAEvaluation.requires_escalation`; no añadir `reference_time` a `SLAEvaluation` ni modificar ADR-002
- [ ] T008 Verificar que `src/domain/` siga importando solo stdlib y módulos propios mediante `src/domain/ruff.toml` y `pyproject.toml`, sin suppressions nuevas

**Checkpoint**: T005 falló antes de T006/T007 y luego pasó en verde antes de continuar.

---

## Phase 3: Foundational — Puerto, SQLite y DTOs de aplicación

**CRITICAL**: bloquea US1, US2 y US3.

- [ ] T009 Escribir y ejecutar las pruebas RED del puerto y SQLite en `tests/test_spec_003_lifecycle_sla.py`, incluyendo `test_port_atomic_insert_concurrent` con altas concurrentes que comprueben que el original no se sobrescribe, migración legacy, `idx_incidents_dup_key`, hidratación y persistencia efímera; registrar el fallo en `evidence/H003-red-green.md` y no implementar aún
- [ ] T010 Ajustar `IncidentRepositoryPort` en `src/application/ports.py` según `data-model.md` → `IncidentRepositoryPort.save_incident`, `IncidentRepositoryPort.supports_persistent_writes`, `IncidentRepositoryPort.get_incident`, `IncidentRepositoryPort.find_open_duplicates` e `IncidentRepositoryPort.list_active_incidents`, sin comprobación previa de existencia
- [ ] T011 Actualizar `src/adapters/outbound/sqlite_repository.py` para inserción atómica, migración aditiva, `idx_incidents_dup_key`, hidratación y filtros de duplicado, conservando `data-model.md` → `Incident.recommended_team`, `Incident.duplicate_group_key`, `Incident.status`, `Incident.incident_id`, `Incident.created_at` y el criterio H002 de OPEN/IN_PROGRESS en `list_active_incidents`
- [ ] T012 Verificar en `src/adapters/outbound/factory.py` que `sqlite:///:memory:` siga siendo el default y que `DATABASE_URL` no se filtre a dominio ni aplicación; la capacidad efímera se expresa solo mediante el puerto
- [ ] T013 Definir en `src/application/dtos.py` las dataclasses `IncidentCreatedResult` e `IncidentSLAResult` según `data-model.md`, con `IncidentCreatedResult.incident_id/title/component/severity/created_at/status/resolved_at/recommended_team/duplicate_group_key/rationale/consistency_ratio/is_duplicate/duplicate_of` e `IncidentSLAResult.incident_id/reference_time/elapsed_minutes/allowed_minutes/remaining_minutes/is_breached/requires_escalation`; usar tipos del dominio cuando corresponda y no importar Pydantic ni esquemas de `src/adapters/inbound/api/schemas.py`

**Checkpoint**: puerto, migración, atomicidad y DTOs de aplicación listos; T009 en verde.

---

## Phase 4: User Story 1 — Registrar el incidente entrante (P1) MVP

**Goal**: registro completo y persistente con respuesta observable por REST y CLI.

**Independent Test**: registrar con almacenamiento persistente por REST y CLI; verificar 201/JSON, ID, fecha local, OPEN, clasificación, sin duplicado, E011 sin sobrescritura y E015 sin falso éxito.

- [ ] T014 [US1] Escribir y ejecutar las pruebas RED `test_bdd_e001_create_valid`, `test_bdd_e002_blank_input`, `test_bdd_e011_duplicate_id`, `test_bdd_e013_invalid_initial_status`, `test_bdd_e014_create_parity` y `test_bdd_e015_ephemeral_storage` en `tests/test_spec_003_lifecycle_sla.py` con `TestClient`/`CliRunner`; registrar el fallo en `evidence/H003-red-green.md` y no implementar aún
- [ ] T015 [US1] Implementar `create_incident` y los errores `IncidentNotFoundError`/`PersistentStorageUnavailableError` en `src/application/services.py`, recibiendo `title` y `raw_text` como entrada del caso de uso sin aceptar esquemas Pydantic; validar valores equivalentes a `data-model.md` → `CreateIncidentRequest.title/raw_text/incident_id/created_at/status`, clasificar con `raw_text`, no persistir ni devolver `raw_text`, y devolver `IncidentCreatedResult` según `data-model.md` → `Incident.*`, `TriageResult.severity/component/rationale/consistency_ratio/recommended_team/duplicate_group_key` e `IncidentCreatedResult.*`; ID repetido se traduce a 422/código 1 sin sobrescritura y sin HTTP 409
- [ ] T016 [US1] Crear en `src/adapters/inbound/api/schemas.py` los esquemas HTTP `CreateIncidentRequest` e `IncidentCreatedResponse`, mapeando desde/hacia `IncidentCreatedResult` sin duplicar validaciones de negocio y sin exponer `raw_text` en la respuesta
- [ ] T017 [P] [US1] Registrar `POST /api/v1/incidents` en `src/adapters/inbound/api/app.py`, delegando en `IncidentService` y mapeando 201/422/503; equivalente abierto con 201 y aviso, ID existente con 422 sin sobrescritura y sin HTTP 409
- [ ] T018 [P] [US1] Añadir el comando `create` en `src/adapters/inbound/cli.py`, delegando en `IncidentService`, imprimiendo el mismo JSON y usando código `1` ante errores
- [ ] T019 [US1] Ejecutar GREEN de US1 en `tests/test_spec_003_lifecycle_sla.py` y registrar el resultado en `evidence/H003-red-green.md`; verificar E011, E014 y E015 antes de cerrar el incremento

**Checkpoint**: US1 permite el registro completo por REST y CLI.

---

## Phase 5: User Story 2 — Avisar de equivalentes abiertos (P1)

**Goal**: completar la detección de duplicados sobre el registro ya funcional.

**Independent Test**: registrar con `duplicate_group_key` coincidente en OPEN/IN_PROGRESS/ESCALATION_REQUIRED y verificar `is_duplicate`/`duplicate_of`; repetir con solo RESOLVED o sin coincidencia.

- [ ] T020 [US2] Escribir y ejecutar las pruebas RED `test_bdd_e003_open_duplicate` y `test_bdd_e004_no_duplicate` en `tests/test_spec_003_lifecycle_sla.py`, usando las interfaces de US1; registrar el fallo en `evidence/H003-red-green.md` y no implementar la lógica aún
- [ ] T021 [US2] Componer el aviso en `src/application/services.py` mediante `find_open_duplicates`, aplicando `data-model.md` → `TriageResult.duplicate_group_key`, `Incident.duplicate_group_key`, `Incident.status`, `Incident.incident_id`, `IncidentCreatedResult.is_duplicate` e `IncidentCreatedResult.duplicate_of`, sin alterar `list_active_incidents` ni usar HTTP 409
- [ ] T022 [US2] Ejecutar GREEN de US2 en `tests/test_spec_003_lifecycle_sla.py`, registrar el resultado y verificar que H002 conserva sus aserciones

**Checkpoint**: US2 completa la detección de duplicados sin romper el registro ni H002.

---

## Phase 6: User Story 3 — Auditar el SLA por ambas interfaces (P2)

**Goal**: auditoría SLA equivalente por REST y CLI con `reference_time` efectivo y errores claros.

**Independent Test**: fijar referencia, consultar el mismo incidente en REST y CLI sobre el mismo archivo SQLite y comparar JSON completo.

- [ ] T023 [US3] Escribir y ejecutar las pruebas RED `test_bdd_e005_sla_audit`, `test_bdd_e006_deterministic_p2`, `test_bdd_e007_resolved_sla`, `test_bdd_e008_rest_cli_sla_parity`, `test_bdd_e009_missing_incident`, `test_bdd_e010_invalid_reference` y `test_bdd_e012_incompatible_dates` en `tests/test_spec_003_lifecycle_sla.py`, sembrando el incidente con el alta de US1; registrar el fallo en `evidence/H003-red-green.md` y no implementar aún
- [ ] T024 [US3] Implementar `evaluate_incident_sla` en `src/application/services.py`, devolviendo `IncidentSLAResult` según `data-model.md` con `incident_id`, `reference_time`, `elapsed_minutes`, `allowed_minutes`, `remaining_minutes`, `is_breached` y `requires_escalation`, usando `SLAEvaluation.elapsed_minutes`, `SLAEvaluation.allowed_minutes`, `SLAEvaluation.remaining_minutes`, `SLAEvaluation.is_breached`, `SLAEvaluation.requires_escalation`, `Incident.severity`, `Incident.created_at` e `Incident.resolved_at`, sin reconstruir estados ni extender `SLAEvaluation`
- [ ] T025 [US3] Añadir en `src/adapters/inbound/api/schemas.py` el esquema HTTP `SLAEvaluationResponse` que mapea desde `IncidentSLAResult`, sin importar DTOs de aplicación en Pydantic ni reglas de negocio
- [ ] T026 [P] [US3] Registrar `GET /api/v1/incidents/{incident_id}/sla` en `src/adapters/inbound/api/app.py`, delegando en `IncidentService` y mapeando 200/404/422, sin HTTP 409
- [ ] T027 [P] [US3] Añadir el comando `sla` en `src/adapters/inbound/cli.py`, delegando en `IncidentService`, imprimiendo el mismo JSON y usando código `1` ante errores
- [ ] T028 [US3] Ejecutar GREEN de US3 en `tests/test_spec_003_lifecycle_sla.py`, registrar el resultado y verificar 120/480/360, `false`, `false`, resueltos y paridad E008

**Checkpoint**: US3 completa la auditoría SLA por REST y CLI.

---

## Phase 7: Verificación integral y evidencias

**Purpose**: calidad, regresiones, manual persistente y evidencia real.

- [ ] T029 Ejecutar `uv run ruff check src/` y corregir infracciones respetando TID251/TID252 en `pyproject.toml`, `src/domain/ruff.toml`, `src/application/ruff.toml` y `src/adapters/inbound/ruff.toml`, sin suppressions nuevas
- [ ] T030 Ejecutar `uv run pytest -v` completo y conservar 51 pruebas y 10 subpruebas más 15 escenarios; solo con fallo real de fixture se ajusta la preparación en `tests/test_spec_002_summary.py`, sin eliminar pruebas ni debilitar aserciones
- [ ] T031 Ejecutar `cli create` y `cli sla` con `DATABASE_URL` de archivo SQLite aislado según `quickstart.md` y `contracts/incidents.md`, registrando comandos, códigos y salidas en `evidence/H003-manual.md`
- [ ] T032 Escribir `evidence/H003-verificacion.md` con salida real de Ruff, pytest, comandos CLI, cobertura E001–E015 y `git status --short`; no afirmar resultados no ejecutados
- [ ] T033 Revisar `specs/003-incident-lifecycle-sla/tasks.md`; cada casilla marcada debe apuntar a evidencia real en `evidence/`

**Checkpoint**: evidencia real disponible antes de cualquier marcado.

---

## Dependencies & Execution Order

- **Phase 1**: sin dependencias; T001 y T002 pueden ejecutarse en paralelo.
- **Phase 2**: depende de Phase 1; T005 (RED) precede a T006/T007.
- **Phase 3**: depende de Phase 2; T009 (RED) precede a T010/T011/T012/T013.
- **US1**: depende de Phase 3; T014 RED → T015–T018 implementación → T019 GREEN.
- **US2**: depende de US1; T020 RED → T021 → T022 GREEN, reutilizando interfaces de US1.
- **US3**: depende de US1 y Phase 2/3; T023 RED → T024/T025 → T026/T027 → T028 GREEN.
- **Phase 7**: depende de US1, US2 y US3; T032 se ejecuta después de T029–T031.
- **Paralelismo real**: T001/T002; T017/T018 tras T016; T026/T027 tras T025. El resto comparte archivos o depende de RED→GREEN.

## Implementation Strategy

1. **MVP**: Phase 1 → Phase 2 → Phase 3 → US1 completo; validar y detenerse.
2. **Incremental**: añadir US2 y después US3; cada fase cierra con GREEN y evidencia.
3. **Final**: Phase 7 con Ruff, pytest, CLI persistente y evidencia.

## BDD Traceability (E001–E015)

| Escenario | Tareas |
|---|---|
| E001 | T004, T014, T015, T016, T017, T018, T019, T031 |
| E002 | T014, T015, T016, T017, T018, T019, T030 |
| E003 | T009, T011, T020, T021, T022 |
| E004 | T009, T011, T020, T021, T022 |
| E005 | T023, T024, T025, T026, T027, T028 |
| E006 | T023, T024, T028, T031 |
| E007 | T005, T007, T023, T024, T028 |
| E008 | T023, T024, T025, T026, T027, T028, T031 |
| E009 | T023, T024, T026, T027, T028 |
| E010 | T005, T023, T024, T026, T027, T028 |
| E011 | T009, T011, T014, T015, T019, T030 |
| E012 | T005, T007, T023, T024, T028 |
| E013 | T014, T015, T016, T017, T018, T019 |
| E014 | T004, T014, T015, T016, T017, T018, T019, T031 |
| E015 | T009, T012, T014, T015, T017, T018, T019, T031 |

## Functional Requirements Traceability (FR-001–FR-015)

| Requisito | Tareas |
|---|---|
| FR-001 | T014, T015, T016, T017, T018 |
| FR-002 | T014, T015, T016, T017, T018, T019 |
| FR-003 | T006, T007, T014, T015, T016 |
| FR-004 | T014, T015, T016, T017, T018 |
| FR-005 | T006, T011, T015, T016, T021 |
| FR-006 | T009, T011, T020, T021 |
| FR-007 | T020, T021, T022 |
| FR-008 | T011, T021, T030 |
| FR-009 | T023, T024, T025, T026, T027 |
| FR-010 | T007, T023, T024, T028 |
| FR-011 | T005, T007, T023, T024 |
| FR-012 | T005, T023, T024, T026, T027 |
| FR-013 | T014, T019, T023, T028, T031 |
| FR-014 | T014, T015, T016, T017, T018 |
| FR-015 | T009, T012, T014, T015, T017, T018, T019, T031 |

## Success Criteria Traceability (SC-001–SC-006)

| Criterio | Tareas |
|---|---|
| SC-001 | T004, T009, T014, T019, T020, T022, T023, T028, T030 |
| SC-002 | T011, T014, T015, T016, T017, T018, T019, T031 |
| SC-003 | T009, T011, T020, T021, T022 |
| SC-004 | T005, T007, T023, T024, T028 |
| SC-005 | T014, T016, T017, T018, T019, T023, T025, T026, T027, T028, T031 |
| SC-006 | T001, T003, T008, T011, T021, T030, T033 |

La matriz usa exclusivamente tareas T001–T033 existentes; no crea tareas nuevas. Cada criterio se verifica con las tareas listadas y su evidencia en `evidence/`.

## Notes

- RED→GREEN: T005, T009, T014, T020 y T023 ejecutan primero la prueba, registran el fallo esperado en `evidence/H003-red-green.md` y solo después habilitan la implementación; T019, T022 y T028 registran el GREEN.
- Los DTOs de aplicación viven en `src/application/dtos.py` como dataclasses; no importan Pydantic ni esquemas de los adaptadores primarios. Los esquemas HTTP son `CreateIncidentRequest`, `IncidentCreatedResponse` y `SLAEvaluationResponse`.
- `raw_text` solo se usa como entrada del triaje: no se persiste, no es campo de `Incident` y no se devuelve en REST ni CLI.
- HTTP 409 no está aprobado ni aparece en el contrato: equivalente abierto se registra con 201 y aviso; `incident_id` existente se rechaza con 422/código 1 sin sobrescritura; almacenamiento efímero mantiene 503/código 1.
- Las citas de campos quedan embebidas en T006, T007, T011, T013, T015, T021 y T024; la trazabilidad de los seis campos de `TriageResult` está en T015 y T021 sin duplicar reglas ni una matriz adicional de campos. La matriz de SC-001–SC-006 es independiente y no añade tareas.
- La duplicación documental detectada por Analyze correspondía a las notas obsoletas sobre `tasks.md` y ya se eliminó; el conteo correcto del informe es 4 HIGH y 3 MEDIUM.
- Se conservan 15 escenarios BDD, 15 requisitos funcionales y 6 criterios de éxito; no se marcan tareas completadas.
- Durante esta curaduría no se modificó código; durante la implementación autorizada sí se modificarán `src/` y `tests/` según las tareas. Fuera de alcance: Constitución, ADR y dependencias (`pyproject.toml`, `uv.lock`).
- No ejecutar `/speckit.analyze` ni `/speckit.implement` desde esta lista; no crear commits; no marcar casillas sin evidencia real.
