# Verificación H004

Fecha: 2026-11-24

## RED

Comando: `uv run pytest -q tests/test_spec_004_runtime_health.py -p no:cacheprovider`

Resultado real: `4 failed, 2 passed, 1 warning`.

Fallos esperados por funcionalidad ausente:

- E001 y E002: `GET /health` devuelve 404.
- E005: la fábrica rechaza `postgresql://` con `ValueError`.
- E006: faltan `Dockerfile`, `.dockerignore` y `docker-compose.yml`.

E003 y E004 ya pasaban con el comportamiento SQLite previo.

## GREEN

Comando: `uv run ruff check src/`

Resultado real: `All checks passed!` (exit 0).

Comando: `uv run pytest -v`

Resultado real: `94 passed, 1 warning, 10 subtests passed` (exit 0). La línea base de 88 pruebas y 10 subpruebas se conserva; se añaden 6 pruebas BDD de H004.

Comando: `uv run python -m src.adapters.inbound.cli health`

Resultado real: `{"status": "ok", "database": "connected"}` (exit 0).

## Validación real de Docker Compose (cierre)

Limitación inicial superada: cuando se registró el RED/GREEN no había daemon Docker disponible. La validación real se ejecutó después de corregir el ciclo de vida de la conexión PostgreSQL.

Resultados confirmados:

- Dos arranques consecutivos satisfactorios.
- Contenedores `api` y `db` healthy.
- `GET /health`: HTTP 200, `{"status":"ok","database":"connected"}`.
- Ruff: `All checks passed!`.
- pytest: `96 passed, 1 warning, 10 subtests passed in 3.84s`.
- CLI health: conectado.

## Incidente de integración (evidencia reportada por el usuario)

- `db` healthy; `api` unhealthy.
- `GET /health` devuelve 503 con `{"status": "error", "database": "unavailable"}`.
- `psycopg.connect` con el `DATABASE_URL` del contenedor `api` conecta y `SELECT 1` devuelve `(1,)`.
- Traza dentro del contenedor `api`: `check_health OperationalError the connection is closed`.
- `from src.adapters.outbound.factory import create_repository` produce `ImportError`; el símbolo real de fábrica es `repository_factory`.

## Diagnóstico definitivo

- En `psycopg` 3.3.9, `Connection.__exit__` hace `commit()`/`rollback()` y cierra la conexión si no pertenece a un pool.
- `_init_schema()` usaba `with conn:` y `save_incident()` usaba `with self._connection() as conn:`. En ambos casos el bloque cerraba la conexión al salir.
- `_connect()` terminaba devolviendo `self._conn` ya cerrado; entonces `check_health()` ejecutaba `SELECT 1` sobre esa conexión cerrada, capturaba `OperationalError` y devolvía `False`, produciendo el 503 de `/health`.
- Las mismas transiciones podían afectar a `save_incident`, `get_incident`, `find_open_duplicates` y `list_active_incidents` al reutilizar una conexión cerrada.

## Corrección aplicada

- `src/adapters/outbound/postgres_repository.py`: `_connect()` crea la conexión, inicializa el esquema, hace `commit()` explícito y solo hace `rollback()`/`close()` si falla la inicialización.
- `_init_schema()` ya no usa `with conn:`; ejecuta DDL y semillas dentro de la transacción controlada por `_connect()`.
- `save_incident()` ya no usa `with self._connection() as conn:`; ejecuta el `INSERT`, lee `rowcount`, hace `commit()` explícito y usa `rollback()` ante errores, sin cerrar la conexión.
- `get_incident()`, `find_open_duplicates()`, `list_active_incidents()` y `check_health()` siguen usando `_connection()` directamente, sin gestores que cierren la conexión.
- `__enter__`, `__exit__` y `close()` siguen siendo los únicos responsables del ciclo de vida: la conexión permanece abierta durante todas las operaciones del repositorio y se cierra al salir del contexto.
- `src/adapters/outbound/factory.py`: se expone `create_repository` como alias público de `repository_factory`, conservando la fábrica canónica y su firma `@contextmanager`.
- La lectura de `SELECT 1` sigue centralizada en `_first_row_value`, que acepta filas tipo `dict` de `dict_row` y filas tipo tupla `(1,)`.
- `tests/test_spec_004_runtime_health.py`: nuevas regresiones `test_regression_health_select_one_tuple_and_factory_alias` y `test_regression_connection_lifecycle_stays_open_until_repository_exit`; esta última simula el cierre de psycopg al usar `with conn` y verifica que el repositorio nunca lo usa, mantiene la conexión abierta en todas las operaciones y la cierra solo al salir.
- No se eliminó el volumen, no se cambiaron credenciales, reglas de negocio, Constitución, ADR ni configuración Docker; `/health` sigue siendo un chequeo real y no se simula un 200.

## Verificación tras la corrección

Comando: `uv run ruff check src/`

Resultado real: `All checks passed!` (exit 0).

Comando: `uv run pytest -v`

Resultado real: `96 passed, 1 warning, 10 subtests passed` (exit 0). Se conservan las 95 pruebas y 10 subpruebas existentes; se añade una regresión de ciclo de vida, quedando 8 pruebas de H004.

Cierre: SC-004 queda evidenciado con dos arranques consecutivos, ambos servicios healthy y salud real sobre `/health`. T019 se marca completada en `specs/004-postgres-container-runtime/tasks.md`.

