# Evidencia H003 — Línea base (T003)

Fecha: 2026-11-24. Rama: `practica-guiada-sdd-semana-2`. Python del sistema: 3.14.7; entorno `uv`: Python 3.12.14.

## Comandos ejecutados y resultados reales

`uv sync --locked`: `Resolved 41 packages in 2ms` / `Checked 34 packages in 351ms`; `pyproject.toml` y `uv.lock` sin cambios.

`uv run ruff check src/`:

```text
All checks passed!
```

`uv run pytest -v` (salida final):

```text
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\YeisonForero\Desktop\Talleres ISIA\Talleres-ISIA\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============== 51 passed, 1 warning, 10 subtests passed in 1.41s ==============
```

La línea base coincide con `evidence/H002-verificacion.md`: 51 pruebas y 10 subpruebas. `git status --short` estaba vacío antes de cualquier edición, y `AGENTS.md` y `.specify/feature.json` no tenían cambios (T001).
