# Contract: Health y runtime — H004

**Feature**: [spec.md](../spec.md) | **Model**: [data-model.md](../data-model.md)

## REST: `GET /health`

| Situación | Estado | Cuerpo |
|---|---|---|
| `check_health()` = `True` | 200 | `{"status":"ok","database":"connected"}` |
| `check_health()` = `False` | 503 | `{"status":"error","database":"unavailable"}` |

- El cuerpo es exactamente ese objeto JSON, sin envoltorio `detail` ni campos adicionales.
- `HealthResponse` declara `status` y `database` como cadenas; la respuesta 503 se documenta con el mismo esquema.
- La comprobación ejecuta `SELECT 1` real sobre la base elegida por `DATABASE_URL`; no se sirve desde caché ni estado estático.

## CLI: comando `health`

```sh
python -m src.adapters.inbound.cli health
```

| Situación | `stdout` | Código de salida |
|---|---|---|
| Conectividad disponible | `{"status":"ok","database":"connected"}` | 0 |
| Sin conectividad | `{"status":"error","database":"unavailable"}` | 1 |

El JSON se emite en `stdout` en ambos casos; no se añade texto en `stderr` ni un formato de error distinto. REST y CLI comparten `IncidentService.check_health()` y devuelven el mismo par `status`/`database`.

## Selección de adaptador (contrato interno de composición)

| Entrada | Resultado |
|---|---|
| `DATABASE_URL` ausente | Repositorio SQLite sobre `sqlite:///:memory:` |
| `DATABASE_URL=sqlite:///...` | Repositorio SQLite sobre la ruta indicada |
| `DATABASE_URL=postgresql://...` | Repositorio PostgreSQL con `dict_row` y SQL con `%s` |
| Otro esquema | `ValueError` de configuración; sin caída a SQLite |

## Orquestación

`docker-compose.yml` declara `db` (`postgres:16-alpine`, volumen persistente, healthcheck `pg_isready`) y `api` (`DATABASE_URL` hacia `db`, `depends_on` con `service_healthy`, healthcheck sobre `/health`). `Dockerfile` usa `python:3.12-slim` con `uv`; `.dockerignore` reduce el contexto de construcción. Ver [quickstart.md](../quickstart.md) para la validación observable.
