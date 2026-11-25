# Data Model: H004 — Persistencia dedicada y runtime en contenedores

**Feature**: [spec.md](../spec.md) | **Decisions**: [research.md](research.md)

## Resultado de salud

No se persiste; es el contrato observable de `GET /health` y del comando `health`.

| Campo | Valores | Regla |
|---|---|---|
| `status` | `ok`, `error` | `ok` solo si `check_health()` devolvió `True`; `error` si devolvió `False`. |
| `database` | `connected`, `unavailable` | Se emite junto con `status` en el mismo JSON; nunca se mezclan. |

Cuerpos exactos: `{"status":"ok","database":"connected"}` y `{"status":"error","database":"unavailable"}`.

## Configuración de persistencia

| `DATABASE_URL` | Adaptador | Persistencia | Regla |
|---|---|---|---|
| ausente | SQLite | `sqlite:///:memory:` | Valor por defecto; efímero, apto para salud, no para altas H003. |
| `sqlite:///...` | SQLite | Archivo indicado | `:memory:` conserva su semántica efímera actual. |
| `postgresql://...` | PostgreSQL | Base dedicada del servicio `db` | Conexión y `SELECT 1` reales; sin ORM. |
| otro esquema | — | — | Error de configuración en la fábrica; sin fallback. |

La selección vive en la composición de salida; dominio y aplicación desconocen esquemas, drivers y credenciales.

## Esquema relacional compartido

Ambos adaptadores conservan las mismas columnas y tipos lógicos. Los timestamps son `TEXT` ISO 8601 en los dos motores.

| Tabla | Columnas | Índices / reglas |
|---|---|---|
| `incidents` | `incident_id TEXT PK`, `title TEXT NOT NULL`, `component TEXT NOT NULL`, `severity TEXT NOT NULL`, `status TEXT NOT NULL`, `created_at TEXT NOT NULL`, `resolved_at TEXT`, `recommended_team TEXT`, `duplicate_group_key TEXT` | `idx_incidents_component_status (component, status)` e `idx_incidents_dup_key (duplicate_group_key, status)`. Inserción atómica con `DO NOTHING` en `incident_id`; nunca `DO UPDATE`. |
| `sla_policies` | `severity TEXT PK`, `max_resolution_minutes INTEGER NOT NULL`, `operates_24x7 INTEGER NOT NULL` | Sembrado con `ON CONFLICT(severity) DO UPDATE` solo si cambiaron los valores; mismo comportamiento que SQLite. |

`created_at`/`resolved_at` se serializan con `.isoformat()` y se hidratan con `datetime.fromisoformat()`. El cálculo SLA permanece en el dominio; SQL solo filtra y ordena.

## Entorno orquestado

| Entidad | Atributos observables | Relación |
|---|---|---|
| `db` | imagen `postgres:16-alpine`, volumen persistente, healthcheck `pg_isready` | Debe estar healthy antes de iniciar `api`. |
| `api` | `DATABASE_URL` hacia `db`, `depends_on: service_healthy`, healthcheck sobre `/health` | Expone el resultado de salud de la base configurada. |

No hay transiciones de estado nuevas: el chequeo es de solo lectura y no modifica incidentes.
