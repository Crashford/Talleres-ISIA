# Evidencia H003 — Verificación integral

Fecha: 2026-11-24. Rama: `practica-guiada-sdd-semana-2` (sin cambios de rama, commits ni publicación). Python del entorno: 3.12.14; Python del sistema: 3.14.7.

## Calidad

Comando: `uv run ruff check src/`.

```text
All checks passed!
```

TID251/TID252 se mantienen en `pyproject.toml` y los `ruff.toml` jerárquicos; no se añadieron suppressions ni dependencias. `pyproject.toml` y `uv.lock` permanecen sin cambios (`uv sync --locked` fue exitoso).

## Pruebas

Comando: `uv run pytest -v`.

```text
collected 88 items
...
============== 88 passed, 1 warning, 10 subtests passed in 2.51s ==============
```

Línea base H001/H002: 51 pruebas y 10 subpruebas (`evidence/H003-baseline.md`). Se añadieron 37 pruebas en `tests/test_spec_003_lifecycle_sla.py`: 15 de normalización temporal/puerto/fábrica y 22 casos BDD (algunos parametrizados) para E001–E015. Ninguna prueba anterior se eliminó; la única preparación ajustada fue la documentada en `evidence/H003-red-green.md` para `test_repository_port_and_sql` (H07).

Advertencia pendiente, heredada de H002: `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` No se cambió la dependencia porque el alcance de H003 no autoriza nuevas dependencias.

## Cobertura BDD E001–E015

| Escenario | Función de aceptación | Resultado |
|---|---|---|
| E001 | `test_bdd_e001_create_valid` | PASSED |
| E002 | `test_bdd_e002_blank_input` | PASSED (4 parámetros) |
| E003 | `test_bdd_e003_open_duplicate` | PASSED (OPEN, IN_PROGRESS, ESCALATION_REQUIRED) |
| E004 | `test_bdd_e004_no_duplicate` | PASSED |
| E005 | `test_bdd_e005_sla_audit` | PASSED |
| E006 | `test_bdd_e006_deterministic_p2` | PASSED (120/480/360, false, false) |
| E007 | `test_bdd_e007_resolved_sla` | PASSED |
| E008 | `test_bdd_e008_rest_cli_sla_parity` | PASSED |
| E009 | `test_bdd_e009_missing_incident` | PASSED |
| E010 | `test_bdd_e010_invalid_reference` | PASSED (2 parámetros) |
| E011 | `test_bdd_e011_duplicate_id` | PASSED (REST, CLI y concurrencia) |
| E012 | `test_bdd_e012_incompatible_dates` | PASSED |
| E013 | `test_bdd_e013_invalid_initial_status` | PASSED (RESOLVED y desconocido) |
| E014 | `test_bdd_e014_create_parity` | PASSED |
| E015 | `test_bdd_e015_ephemeral_storage` | PASSED |

Ejecución completa del archivo H003: `37 passed, 1 warning in 3.18s`. Las fases RED y GREEN de T005, T009, T014, T020 y T023 están registradas en `evidence/H003-red-green.md`.

## Comandos CLI persistentes

Ver `evidence/H003-manual.md`: `create` y `sla` sobre el mismo archivo SQLite, códigos `0` y `0`, con `elapsed_minutes=120`, `allowed_minutes=480`, `remaining_minutes=360`, `is_breached=false`, `requires_escalation=false`. Comando adicional con `sqlite:///:memory:` devolvió código `1` sin respuesta de éxito.

## Estado del árbol de trabajo

Salida real de `git status --short`:

```text
 M specs/003-incident-lifecycle-sla/tasks.md
 M src/adapters/inbound/api/app.py
 M src/adapters/inbound/api/schemas.py
 M src/adapters/inbound/cli.py
 M src/adapters/outbound/sqlite_repository.py
 M src/application/ports.py
 M src/application/services.py
 M src/domain/models.py
 M src/domain/sla_calculator.py
 M tests/conftest.py
 M tests/test_spec_002_summary.py
?? evidence/H003-baseline.md
?? evidence/H003-manual.md
?? evidence/H003-red-green.md
?? evidence/H003-verificacion.md
?? src/application/dtos.py
?? tests/test_spec_003_lifecycle_sla.py
```

## Archivos ignorados

Contenido real de `.gitignore`: `__pycache__/`, `*.py[cod]`, `*$py.class`, `.venv/`, `venv/`, `.env`, `*.db`, `.pytest_cache/`, `.vscode/`. Cubre el entorno virtual, cachés y bases SQLite. El archivo usado en la verificación manual se creó fuera del repositorio (`C:/Users/YEISON~1/AppData/Local/Temp/opencode/h003-manual.db`), por lo que no aparece en `git status --short`. No fue necesario modificar `.gitignore`.

Las 33 casillas de `specs/003-incident-lifecycle-sla/tasks.md` quedaron marcadas `[X]` después de esta verificación. No se crearon commits ni se modificaron Constitución, ADR, spec, plan, contratos ni dependencias.

Comprobación final repetida tras marcar tareas: `uv run ruff check src/` → `All checks passed!`; `uv run pytest -q` → `88 passed, 1 warning, 10 subtests passed in 9.10s`. `.specify/extensions.yml` sigue ausente, por lo que no hay hooks posteriores que ejecutar.

## Limitaciones verificadas

- H003 no expone `GET` por ID ni transiciones de estado; E007 usa datos resueltos sembrados, según el alcance aprobado.
- El texto P2 de los ejemplos documentados clasifica como P3 con el motor vigente; se usó otro texto con indicios de latencia y volumen para el caso determinista, sin alterar las reglas de triaje.
- La consola PowerShell mostró caracteres acentuados sustituidos por `?` en la salida; los archivos y las pruebas usan cadenas Unicode correctas.
- Ruff verifica las fronteras estáticas configuradas; no constituye una demostración exhaustiva de dependencias dinámicas.
