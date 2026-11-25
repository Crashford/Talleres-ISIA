# Implementation Plan: H004 — Persistencia dedicada y runtime en contenedores

**Branch**: `practica-guiada-sdd-semana-2` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Status**: plan generado para `/speckit.tasks`; pendiente de aprobación humana. No se implementa código, no se instalan dependencias y no se cambia de rama.

> `setup-plan.sh` informó `BRANCH=004-postgres-container-runtime` porque deriva el identificador de `.specify/feature.json`. La rama Git verificada es `practica-guiada-sdd-semana-2` y permanece activa.

## Summary

Añadir un chequeo de salud basado en `SELECT 1` real, compartido por REST y CLI, y un adaptador PostgreSQL que implemente el mismo puerto que SQLite. La fábrica selecciona el adaptador únicamente por `DATABASE_URL`, con SQLite en memoria por defecto. La composición organiza `api`/`db` con `postgres:16-alpine`, volumen persistente, `pg_isready` y healthcheck sobre `/health`, sin tocar triaje, SLA ni contratos H001–H003.

## Technical Context

- **Language/Version**: Python >=3.10 gestionado con `uv`; imagen `python:3.12-slim` en contenedores.
- **Primary Dependencies**: FastAPI, Pydantic v2 y Typer existentes; `psycopg[binary]>=3.3.9` ya declarado en `pyproject.toml`/`uv.lock` del árbol de trabajo (no instalado en esta fase); Ruff, pytest y httpx para calidad. Sin ORM.
- **Storage**: SQLite3 estándar por defecto (`sqlite:///:memory:`) y PostgreSQL 16 dedicado vía `psycopg`; timestamps `TEXT` ISO 8601 en ambos motores.
- **Testing**: pytest con `TestClient`, `CliRunner`, dobles del puerto y archivos Docker leídos como texto. Línea base verificada: 88 pruebas y 10 subpruebas; sin Docker ni PostgreSQL activo en pytest.
- **Target Platform**: backend REST/CLI y orquestación Docker Compose reproducible.
- **Project Type**: proyecto Python único con arquitectura hexagonal existente.
- **Performance Goals**: salud ejecuta un `SELECT 1`; no se inventa umbral de latencia adicional.
- **Constraints**: Constitución 1.1.0, ADR-004, skills `hexagonal-architecture` y `bdd-acceptance`, spec E001–E006; sin funcionalidades nuevas fuera del taller.
- **Scale/Scope**: componentes enumerados por el usuario: `postgres_repository.py`, `factory.py`, `services.py`, API, CLI, `Dockerfile`, `.dockerignore`, `docker-compose.yml` y `tests/test_spec_004_runtime_health.py`.
- **Clarifications antes de Phase 0** (`NEEDS CLARIFICATION`, resueltas): healthcheck HTTP sin `curl` (R7); pruebas PostgreSQL sin servicio real (R6); inserción atómica frente a `ON CONFLICT DO UPDATE` (R4); flujo de salida de la CLI `health` (R9); importación diferida del driver (R2). Todo resuelto en [research.md](research.md); no quedan marcadores pendientes.

## Constitution Check

*GATE: superado antes de Phase 0 y revalidado tras Phase 1.*

| Principio | Verificación | Resultado |
|---|---|---|
| I — Dominio determinista único | Triaje y SLA no se modifican; `check_health()` es un caso de uso sobre el puerto existente y no calcula reglas de negocio. | PASS |
| II — Hexagonal estricta | Dominio/aplicación sin HTTP, CLI, drivers ni ORM; REST y CLI delegan en `IncidentService`; `DATABASE_URL` y `psycopg` quedan en adaptadores de salida; Ruff TID251/TID252 se conserva. | PASS |
| III — SLA y estados | Políticas, estados y criterio de activos de H002 intactos; la salud es solo lectura. | PASS |
| IV — Paridad y aceptación verificable | Un mismo caso de uso para REST y CLI; JSON exacto y códigos 200/503 y 0/1; seis escenarios BDD con almacenamiento aislado. | PASS |
| V — Calidad y simplicidad | `uv`, FastAPI, Pydantic, Typer y Ruff/pytest existentes; `psycopg[binary]` según ADR-004; sin ORM ni dependencias añadidas en esta fase. | PASS |
| VI — Persistencia dual y paridad temporal | Dos adaptadores tras `IncidentRepositoryPort`; default `sqlite:///:memory:`; timestamps `TEXT` ISO 8601; filtrado parametrizado, JOIN e índice compuesto conservados. | PASS |
| VII — Despliegue reproducible | Compose define `api` y `db`; `db` usa `postgres:16-alpine`; `depends_on: service_healthy`; healthcheck de `api` sobre `/health`. | PASS |

**Gate**: PASS. No hay violaciones que justificar en *Complexity Tracking*.

## Project Structure

```text
specs/004-postgres-container-runtime/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/health.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md                       # No creado por /speckit.plan
src/
├── domain/                        # Sin cambios
├── application/
│   └── services.py                # Añadir check_health()
├── adapters/
│   ├── inbound/
│   │   ├── api/{app,schemas}.py   # HealthResponse y GET /health
│   │   └── cli.py                 # Comando health
│   └── outbound/
│       ├── factory.py             # Selección por DATABASE_URL
│       ├── sqlite_repository.py   # Sin cambios funcionales
│       └── postgres_repository.py # Nuevo adaptador
Dockerfile
.dockerignore
docker-compose.yml
tests/
├── conftest.py                    # Sin cambios
└── test_spec_004_runtime_health.py # Nuevos escenarios E001–E006
```

**Structure Decision**: conservar el proyecto único y la frontera hexagonal. No se crean paquetes paralelos, nuevos adaptadores primarios ni motores adicionales. `pyproject.toml`/`uv.lock` ya contienen la dependencia en el árbol de trabajo; este plan no la modifica.

## Diseño técnico

1. **Aplicación**: `IncidentService.check_health()` obtiene el repositorio mediante la fábrica inyectada, delega en `repo.check_health()` y devuelve el booleano; sin fábrica devuelve `False`. No importa SQLite, PostgreSQL, HTTP ni CLI.
2. **Repositorio PostgreSQL**: `PostgresIncidentRepository` en `src/adapters/outbound/postgres_repository.py` implementa `IncidentRepositoryPort`, usa `psycopg` con `dict_row`, conexión diferida, SQL parametrizado con `%s`, el mismo esquema y los índices `idx_incidents_component_status` e `idx_incidents_dup_key`, y timestamps `.isoformat()`/`datetime.fromisoformat()`. `check_health()` ejecuta `SELECT 1` y captura `psycopg.Error` → `False`. `supports_persistent_writes()` es `True`. `get_incident`, `find_open_duplicates` y `list_active_incidents` conservan las reglas vigentes sin mover cálculo SLA al SQL.
3. **Fábrica**: `factory.py` respeta `DATABASE_URL` ausente → `sqlite:///:memory:`, `sqlite:///` → SQLite, `postgresql://` → PostgreSQL; cualquier otro esquema mantiene el `ValueError` actual. La importación de `psycopg` se difiere a la rama PostgreSQL para que pytest pueda inyectar un doble sin instalar ni contactar al motor.
4. **API**: `HealthResponse` en `schemas.py` con `status` y `database`; `GET /health` en `app.py` devuelve 200 con el cuerpo de éxito o `JSONResponse` 503 con el cuerpo de error, sin envoltorio `detail`.
5. **CLI**: comando `health` en `cli.py` que imprime el mismo JSON en `stdout` y termina con 0 u 1 según el booleano; la fábrica del módulo se puede sustituir en pruebas.
6. **Contenedores**: `Dockerfile` con `python:3.12-slim` y `uv`; `.dockerignore` para reducir el contexto; `docker-compose.yml` con `db` (`postgres:16-alpine`, volumen persistente, healthcheck `pg_isready`) y `api` (`DATABASE_URL` hacia `db`, `depends_on` con `service_healthy`, healthcheck sobre `/health` mediante `urllib.request`). Credenciales, volumen y puertos son parámetros de despliegue, no lógica de aplicación.
7. **Pruebas**: `tests/test_spec_004_runtime_health.py` usa dobles que cumplen el puerto, `create_app(repo_factory=...)`, `CliRunner` con `monkeypatch`, un doble de `psycopg.connect` y lectura textual de los archivos Docker. Comprueba cuerpos JSON completos, códigos, `SELECT 1`, `%s`, `dict_row`, timestamps ISO 8601 como texto y estructura Compose; no modifica las pruebas existentes.

### Diferencia documentada: `ON CONFLICT DO UPDATE`

La guía del taller menciona `INSERT ... ON CONFLICT DO UPDATE`, pero H003 E011/FR-003/FR-007 exige inserción atómica **sin sobrescribir** un `incident_id` existente: 422 en REST y código 1 en CLI, sin HTTP 409. Por tanto, `incidents` usa `DO NOTHING` y devuelve `False` si no insertó. `DO UPDATE` se mantiene solo en el sembrado de `sla_policies`, igual que en SQLite. Ver [research.md](research.md#r4--inserción-atómica-frente-a-on-conflict-do-update).

### Cobertura BDD E001–E006

| Escenario | Función de aceptación | Foco observable |
|---|---|---|
| E001 | `test_bdd_e001_health_connected` | Doble del puerto con `check_health() = True`; REST 200 y CLI 0 con el JSON exacto. |
| E002 | `test_bdd_e002_health_unavailable` | Doble con `check_health() = False`; REST 503 y CLI 1 sin falso éxito. |
| E003 | `test_bdd_e003_default_sqlite_memory` | Sin `DATABASE_URL`, la fábrica devuelve el adaptador SQLite en memoria. |
| E004 | `test_bdd_e004_sqlite_url` | `sqlite:///...` selecciona SQLite sobre la ruta aislada por `tmp_path`. |
| E005 | `test_bdd_e005_postgres_url_and_timestamps` | `postgresql://...` selecciona PostgreSQL con doble de driver; verifica puerto, `dict_row`, `%s` y timestamps ISO 8601 como texto. |
| E006 | `test_bdd_e006_compose_structure` | Archivos Docker con `python:3.12-slim`, `uv`, `postgres:16-alpine`, volumen, `pg_isready`, `service_healthy` y healthcheck `/health`. |

### Verificación prevista en Build

```sh
uv run ruff check src/
uv run pytest -v
unset DATABASE_URL
uv run python -m src.adapters.inbound.cli health
docker compose config          # evidencia opcional si Docker está disponible
docker compose up --build      # evidencia opcional si Docker está disponible
```

Criterio de evidencia: Ruff sin infracciones; 88 pruebas y 10 subpruebas de la línea base conservadas más las nuevas funciones E001–E006; pytest pasa sin Docker ni PostgreSQL activo. Los resultados reales se registrarán bajo `evidence/` solo después de ejecutar los comandos.

## Riesgos operativos

- La dependencia `psycopg[binary]` está declarada pero no instalada en esta fase; las pruebas deben inyectar el doble y no importar el driver de forma anticipada.
- Un fallo de conexión debe traducirse a `False` en `check_health()` para no convertirlo en 500; un esquema no soportado sigue siendo error de configuración.
- La evidencia de contenedores es independiente de pytest; no se afirma que Docker se haya ejecutado en esta fase.

## Complexity Tracking

Sin desviaciones de la Constitución que requieran justificación. No se añaden motores, ORM, paquetes ni funcionalidades de hitos futuros.
