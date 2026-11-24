# Tasks: H002 — Resumen de incidentes activos

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/summary.md.
**Status**: Aprobado e implementado; pruebas verificadas en CI 45488959530. Pull Request #1 abierto.

## Phase 1: Setup

- [x] T001 Incorporar Ruff mediante uv add --dev ruff y versionar pyproject.toml/uv.lock (CI: 45488140670).
- [x] T002 Configurar Ruff en pyproject.toml y src/domain/ruff.toml, src/application/ruff.toml, src/adapters/inbound/ruff.toml (TID251/TID252).

## Phase 2: Foundation

- [x] T003 Crear pruebas de contrato del puerto, persistencia, consulta SQL e índice en tests/test_spec_002_summary.py.
- [x] T004 Definir puerto IncidentRepositoryPort y DTOs en src/application/ports.py y services.py.
- [x] T005 Extraer SQLiteIncidentRepository en src/adapters/outbound/sqlite_repository.py: esquema, migración compatible de correlación, operaciones del puerto, semilla, JOIN e índice.
- [x] T006 Crear src/adapters/outbound/factory.py con DATABASE_URL, ciclo de vida e inyección; actualizar benchmark src/incident_repository.py.
- [x] T007 Preparar fixtures aisladas de repositorio y aplicación en tests/conftest.py o tests/test_spec_002_summary.py.

## Phase 3: US1 — Resumen global (P1)

- [x] T008 [US1] Crear test_bdd_global_summary (E001), incluyendo exclusión de estados y cálculo SLA, antes de implementar.
- [x] T009 [US1] Implementar get_active_incidents_summary en src/application/services.py usando dominio y puerto, con validación temporal.
- [x] T010 [US1] Crear DTOs de salida Pydantic y GET en src/adapters/inbound/api/{schemas,app}.py, componiendo la fábrica sin afectar triage.
- [x] T011 [US1] Ejecutar prueba E001 y contrato del puerto.

## Phase 4: US2 — Filtro y estado vacío (P2)

- [x] T012 [US2] Crear test_bdd_component_filter (E002) y test_bdd_empty_summary (E003) en tests/test_spec_002_summary.py.
- [x] T013 [US2] Verificar filtro exacto, conteos y ausencia de coincidencias; implementar cualquier comportamiento faltante en servicio, SQL y API.
- [x] T014 [US2] Ejecutar E002/E003 y pruebas de validación temporal y filtro.

## Phase 5: US3 — Paridad CLI (P3)

- [x] T015 [US3] Crear test_bdd_cli_summary_parity (E004) y pruebas de error de CLI.
- [x] T016 [US3] Implementar summary en src/adapters/inbound/cli.py delegando en IncidentService.
- [x] T017 [US3] Verificar salida JSON idéntica, referencia fija y código de salida.

## Phase 6: Verificación

- [x] T018 Actualizar AGENTS.md, README.md y workflow CI para Ruff y comandos H002.
- [x] T019 Ejecutar uv run ruff check src/ y uv run pytest -v; comprobar regresión H001.
- [x] T020 Ejecutar motores, CLI triage/summary y benchmark según quickstart.md; registrar evidencia de resultados y commits.
- [x] T021 Marcar tareas realmente terminadas y abrir Pull Request sin fusionar main.

**Orden**: T001–T007 → US1 → US2 → US3 → verificación. Cada prueba de escenario se escribe antes de su implementación correspondiente; si una función compartida ya satisface otro escenario, se verifica sin introducir cambios artificiales. Las tareas no se marcan por anticipado.

**Evidencia**: [RED](https://github.com/Crashford/Talleres-ISIA/actions/runs/45488841999), [GREEN](https://github.com/Crashford/Talleres-ISIA/actions/runs/45488959530), [PR #1](https://github.com/Crashford/Talleres-ISIA/pull/1). Ver evidence/H002-verificacion.md.
