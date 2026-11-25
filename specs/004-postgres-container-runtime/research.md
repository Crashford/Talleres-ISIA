# Research: H004 — Persistencia dedicada y runtime en contenedores

**Feature**: [spec.md](../spec.md) | **ADR**: [ADR-004](../../docs/adr/004-persistencia-postgresql-y-runtime-contenedores.md) | **Fecha**: 2026-11-24

Las decisiones R1–R9 resuelven los puntos marcados como `NEEDS CLARIFICATION` en el Technical Context de [plan.md](plan.md). No quedan ambigüedades funcionales del taller.

## R1 — Driver y forma de fila

- **Decision**: usar `psycopg[binary]>=3.3.9` con `psycopg.rows.dict_row` en el adaptador PostgreSQL. La dependencia ya está declarada en `pyproject.toml`/`uv.lock` del árbol de trabajo; no se instala ni se modifica en esta fase de planificación.
- **Rationale**: Constitución V/VI y ADR-004 exigen `psycopg[binary]` sin ORM. `dict_row` permite que `_to_incident` lea columnas por nombre, igual que `sqlite3.Row`, sin duplicar lógica en aplicación.
- **Alternatives considered**: `psycopg2` (fuera del ADR), ORM (prohibido), SQLite en producción (no cubre la base dedicada).

## R2 — Selección transparente por `DATABASE_URL`

- **Decision**: la fábrica acepta `postgresql://` y `sqlite:///`, y usa `sqlite:///:memory:` si la variable no existe. Cualquier otro esquema conserva el `ValueError` actual de configuración; nunca hay fallback silencioso. La importación de `psycopg` se difiere a la rama PostgreSQL para permitir pruebas con un doble del módulo.
- **Rationale**: FR-004, Edge Cases y ADR-004; la importación diferida mantiene las pruebas locales independientes de Docker y de una instancia real.
- **Alternatives considered**: aceptar el alias `postgres://` (el taller exige el prefijo exacto `postgresql://`); caer a SQLite ante URL inválida (contradice el contrato de error de configuración).

## R3 — Salud real y traducción de fallos

- **Decision**: `check_health()` ya existe en `IncidentRepositoryPort`. Cada adaptador ejecuta `SELECT 1` y captura sus propios errores de driver (`psycopg.Error` / `sqlite3.Error`), devolviendo `False` también si la apertura de conexión falla. `IncidentService.check_health()` solo delega y devuelve el booleano; sin fábrica configurada devuelve `False`. REST traduce `True` a 200 y `False` a 503; CLI imprime el mismo JSON y termina 0/1.
- **Rationale**: E001/E002, NFR-001 y la regla de paridad REST/CLI; evita respuestas estáticas o falsos éxitos sin filtrar drivers al núcleo.
- **Alternatives considered**: respuesta de salud constante (rechazada), propagar la excepción como 500 (incumple el 503 exigido), memorizar el último resultado (rechazado).

## R4 — Inserción atómica frente a `ON CONFLICT DO UPDATE`

- **Decision**: la tabla `incidents` usa `INSERT ... ON CONFLICT (incident_id) DO NOTHING` y reporta `False` cuando no insertó. `ON CONFLICT DO UPDATE` se conserva únicamente en el sembrado de `sla_policies`, igual que en el adaptador SQLite actual.
- **Rationale**: H003 E011/FR-003/FR-007 exige inserción atómica **sin sobrescribir** un `incident_id` existente; el resultado es 422 en REST y código 1 en CLI, nunca 409. La mención de `DO UPDATE` de la guía del taller no puede aplicarse a `incidents` sin romper el contrato aprobado.
- **Alternatives considered**: `DO UPDATE` en `incidents` (rechazado: sobrescribe y viola H003); consultar y luego insertar (rechazado: condición de carrera).

## R5 — Paridad temporal

- **Decision**: `created_at` y `resolved_at` se escriben como `TEXT` ISO 8601 con `.isoformat()` en ambos motores y se hidratan con `datetime.fromisoformat()`. No se usan tipos temporales nativos de PostgreSQL.
- **Rationale**: Constitución VI, ADR-004 y NFR-003; conserva el cálculo SLA en dominio y evita conversiones dependientes del driver.
- **Alternatives considered**: `TIMESTAMP`/`TIMESTAMPTZ` nativo (rompe paridad con SQLite), epoch numérico (pierde ISO 8601 legible).

## R6 — Pruebas BDD sin Docker ni PostgreSQL activo

- **Decision**: `tests/test_spec_004_runtime_health.py` usa dobles que cumplen `IncidentRepositoryPort`, `create_app(repo_factory=...)`, `CliRunner` con `monkeypatch` de la fábrica del módulo CLI, y un doble de `psycopg.connect` inyectado en la rama PostgreSQL de la fábrica. La estructura Docker se verifica leyendo `Dockerfile`, `.dockerignore` y `docker-compose.yml` como texto. No se crean contenedores ni se conecta a una base real.
- **Rationale**: Constitución y skill `bdd-acceptance`: almacenamiento aislado, sin servicios externos ni datos reales; se conservan las 88 pruebas y 10 subpruebas existentes.
- **Alternatives considered**: Testcontainers o PostgreSQL local en pytest (rechazado: dependencia de infraestructura), comprobar solo el código fuente (insuficiente para el comportamiento observable).

## R7 — Healthcheck del servicio `api`

- **Decision**: el healthcheck de Compose invoca `/health` mediante la biblioteca estándar `urllib.request` desde la imagen `python:3.12-slim`, con salida distinto de cero si el estado no es 200. `db` usa `pg_isready`.
- **Rationale**: FR-006 exige healthcheck sobre `/health`; la imagen base no garantiza `curl`, por lo que no se añade un paquete solo para la sonda.
- **Alternatives considered**: instalar `curl` (paquete innecesario), sondeo TCP (no comprueba el estado devuelto por `/health`).

## R8 — Parámetros de despliegue

- **Decision**: usuario, contraseña, nombre de base, nombre del volumen y publicación de puertos se tratan como parámetros de `docker-compose.yml`; la aplicación solo consume `DATABASE_URL`. El plan no fija credenciales ni introduce variables nuevas en el núcleo.
- **Rationale**: Assumptions de [spec.md](spec.md); evita inventar funcionalidad o secretos fuera del alcance del taller.
- **Alternatives considered**: credenciales incrustadas en código (rechazado), variables adicionales leídas por dominio/aplicación (rechazado por hexagonalidad).

## R9 — Flujo de salida del comando `health`

- **Decision**: el JSON de éxito y el de error se escriben en `stdout`; el código de salida 0/1 distingue el resultado. No se usa un mensaje libre en `stderr` ni el formato `detail` de HTTP.
- **Rationale**: FR-002/FR-003 exigen el mismo JSON en REST y CLI; así `CliRunner` puede comparar el cuerpo completo sin depender del flujo de error. Los comandos H001–H003 conservan su manejo actual.
- **Alternatives considered**: error en `stderr` (rechazado: rompe la paridad de cuerpo observable), texto libre (rechazado: no es verificable).
