# Evidencia H002 — 2026-11-24

Rama: practica-guiada-sdd-semana-2. Pull Request [#1](https://github.com/Crashford/Talleres-ISIA/pull/1), abierto, sin fusión.

## Fase RED
Commit 7d2397bb206e6907022b203c4c3c464a6cf99bc1. [CI 45488841999](https://github.com/Crashford/Talleres-ISIA/actions/runs/45488841999): ambos jobs fallaron en pytest durante colección por ModuleNotFoundError: No module named 'src.adapters.outbound'. Era la ausencia esperada del adaptador, no una ejecución individual de cada escenario.

## Fase GREEN
Commit 3084195a26c724fea8139e46421a4540e0873d45. [CI 45488959530](https://github.com/Crashford/Talleres-ISIA/actions/runs/45488959530): completed/success.

| Verificación | Python 3.10 | Python 3.12 |
|---|---|---|
| uv sync --locked | success | success |
| uv run ruff check src/ | All checks passed! | All checks passed! |
| uv run pytest -v | 51 passed, 10 subtests passed, 1 warning (0.26s) | 51 passed, 10 subtests passed, 1 warning (0.35s) |
| Motores de dominio, CLI triage/summary, benchmark, auditoría de contexto | success | success |

34 casos H001/regresión y 17 casos H002 (incluye parametrización). La advertencia de pytest fue StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead. No se cambia la dependencia indicada en la guía en este hito. También hubo advertencias de deprecación del runtime de acciones Node.

Salida CLI summary por defecto (sin datos): 
```json
{"total_active": 0, "breached_count": 0, "incidents": []}
```

Benchmark de 10.000 registros, 20 ejecuciones: 800 activos en payments-gateway; promedio 8.04 ms (3.10) y 14.74 ms (3.12). Son mediciones del código refactorizado, en runners distintos; no se afirma un porcentaje de mejora sin comparación controlada. Las pruebas verifican una sola consulta SELECT con INNER JOIN e índice compuesto, y filtrado parametrizado.

## Alcance de la práctica
Spec Kit oficial se instaló e inicializó en CI (45487963139). Ruff se instaló en CI (45488140670), y los scripts oficiales de plantillas/prerrequisitos se ejecutaron (45488392099). Los artefactos SDD se elaboraron con ChatGPT siguiendo la guía; no se ejecutaron los comandos interactivos /speckit.* en OpenCode ni se configuró un modelo en OpenCode. No se implementaron H003/H004. TID251/TID252 y revisión de imports cubren las fronteras configuradas, no constituyen una demostración exhaustiva de toda posible dependencia dinámica.

H002 no ofrece escrituras de incidentes por REST/CLI. El adaptador inicializa/migra el esquema y políticas al abrir SQLite. Base predeterminada en memoria vacía, archivo configurable para compartir datos. El lockfile ya está versionado y uv sync --locked fue exitoso.
