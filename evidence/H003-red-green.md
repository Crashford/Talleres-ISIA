# Evidencia H003 — RED/GREEN

Fecha: 2026-11-24. Todas las ejecuciones usan `uv run pytest -v` desde la raíz del repositorio.

## Fase RED — T005 (normalización temporal)

Comando: `uv run pytest -v tests/test_spec_003_lifecycle_sla.py`.

Resultado real: `10 failed, 1 warning in 1.06s`. Las diez pruebas fallaron con `AttributeError: module 'src.domain.sla_calculator' has no attribute 'resolve_created_at' / 'resolve_reference_time' / 'parse_iso_datetime'`, es decir, por la funcionalidad temporal aún no implementada. No se modificó `src/domain/` antes de esta ejecución.

GREEN de la misma prueba tras T006/T007: `10 passed, 1 warning in 0.05s`. `uv run ruff check src/`: `All checks passed!` (T008).

## Fase RED — T009 (puerto, SQLite y capacidad de persistencia)

Comando: `uv run pytest -v tests/test_spec_003_lifecycle_sla.py`.

Resultado real: `5 failed, 10 passed, 1 warning in 0.73s`. Los cinco fallos son exclusivamente de las pruebas nuevas del puerto: `save_incident` devolvía `None` en lugar de `bool`, faltaba `supports_persistent_writes`, faltaba la columna `recommended_team` y el índice `idx_incidents_dup_key` en un esquema legacy. Las diez pruebas temporales ya estaban en verde.

GREEN tras T010–T013: `15 passed, 1 warning in 0.61s`. `uv run ruff check src/`: `All checks passed!`.

## Fase RED — T014 (US1: registro REST/CLI)

Comando: `uv run pytest -v tests/test_spec_003_lifecycle_sla.py -k "bdd_e001 or bdd_e002 or bdd_e011 or bdd_e013 or bdd_e014 or bdd_e015"`.

Resultado real: `10 failed, 15 deselected, 1 warning in 2.21s`. Los diez casos fallaron con `404` en la ruta `POST /api/v1/incidents` aún no registrada; la implementación de usuario no se inició antes de esta ejecución.

GREEN de US1 tras T015–T018 (T019): `10 passed, 15 deselected, 1 warning in 1.31s`; se verificaron E011 (sin sobrescritura, incluida concurrencia), E014 (paridad con almacenamientos aislados) y E015 (503/código 1 sin falso éxito). `uv run ruff check src/`: `All checks passed!`.

## Fase RED — T020 (US2: aviso de equivalentes abiertos)

T015 ya había compuesto el aviso como parte del alta; para ejecutar el RED de US2 se retiró temporalmente esa composición en `src/application/services.py` (`duplicate_of = []`) y se ejecutó `uv run pytest -v tests/test_spec_003_lifecycle_sla.py -k "bdd_e003 or bdd_e004"`.

Resultado real: `3 failed, 1 passed, 25 deselected, 1 warning in 0.70s`. Los tres estados OPEN, IN_PROGRESS y ESCALATION_REQUIRED fallaron con `assert False is True` en `is_duplicate`; E004 (sin coincidencia/RESOLVED) ya pasaba por ser el caso negativo. Se restauró la composición en T021.

GREEN de US2 (T022): `4 passed, 25 deselected, 1 warning in 0.48s`. Regresión H002: `17 passed, 1 warning in 1.22s`.

## Fase RED — T023 (US3: auditoría SLA REST/CLI)

Las pruebas E005–E012 se escribieron antes de cualquier cambio de implementación de esta fase. Como el caso de uso y los adaptadores ya existían desde T015–T018, se retiraron temporalmente la ruta `GET /api/v1/incidents/{incident_id}/sla` y el comando CLI `sla` para reproducir el RED.

Comando: `uv run pytest -v tests/test_spec_003_lifecycle_sla.py -k "bdd_e005 or bdd_e006 or bdd_e007 or bdd_e008 or bdd_e009 or bdd_e010 or bdd_e012"`.

Resultado real: `8 failed, 29 deselected, 1 warning in 6.09s`. Fallos por `404` en la ruta y `No such command 'sla'` en CLI (`exit_code 2`). Se restauraron la ruta y el comando en T024–T027.

GREEN de US3 (T028): `37 passed, 1 warning in 3.18s` para todo el archivo H003, incluidos 120/480/360, `false`, `false`, resueltos y paridad E008. `uv run ruff check src/`: `All checks passed!`.

### Ajuste H002 por fallo real (H07)

`uv run pytest -v tests/test_spec_002_summary.py` falló en `test_repository_port_and_sql` con `duplicate_group_key: 'key' != None`: el puerto aprobado hidrata el campo nuevo y `find_open_duplicates` devuelve identificadores. Se ajustó únicamente la preparación de esa prueba (`a.duplicate_group_key = "key"`, `repo.save_incident(a)`) y la comparación de candidatos a `[a.incident_id]`, sin eliminar pruebas ni debilitar el criterio OPEN/IN_PROGRESS. Resultado real tras el ajuste: `17 passed, 1 warning in 8.01s`.
