# Quickstart: H004 — Health y runtime en contenedores

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/health.md](contracts/health.md) | **Model**: [data-model.md](data-model.md)

## Prerrequisitos

- Python >=3.10 y `uv`.
- Docker con Compose solo para la evidencia opcional de contenedores; **no** es necesario para las pruebas locales.

## Validación local (sin Docker ni PostgreSQL activo)

```sh
uv run ruff check src/
uv run pytest -v

unset DATABASE_URL
uv run python -m src.adapters.inbound.cli health; echo "exit=$?"
DATABASE_URL=sqlite:///incidentops.db uv run python -m src.adapters.inbound.cli health; echo "exit=$?"
```

Resultados esperados:

- Ruff sin infracciones; pytest conserva las 88 pruebas y 10 subpruebas existentes y añade las del nuevo archivo de aceptación.
- Con `DATABASE_URL` ausente o con archivo SQLite accesible: `{"status":"ok","database":"connected"}` y `exit=0`.
- La simulación de pérdida de conectividad se ejecuta dentro de pytest mediante un doble del puerto: `{"status":"error","database":"unavailable"}`, HTTP 503 y `exit=1`. No se requiere una base caída real.
- `tests/test_spec_004_runtime_health.py` valida además la estructura de `Dockerfile`, `.dockerignore` y `docker-compose.yml` leyendo los archivos como texto.

## Validación HTTP opcional

```sh
uv run uvicorn src.adapters.inbound.api.app:app
curl -i http://127.0.0.1:8000/health
```

Conectividad disponible: `HTTP/1.1 200 OK` y el cuerpo de éxito. El cuerpo de error se comprueba en pytest con el doble, para no depender de infraestructura externa.

## Evidencia de contenedores (cuando Docker esté disponible)

```sh
docker compose config
docker compose up --build
docker compose ps
```

Esperado: `db` alcanza `healthy` con `pg_isready` antes de que `api` arranque; el healthcheck de `api` consulta `/health` y solo pasa si la base configurada está conectada. Los valores de credenciales y volumen son parámetros de Compose, no parte del contrato funcional.
