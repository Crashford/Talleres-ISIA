# Feature Specification: H004 — Persistencia dedicada y runtime en contenedores

**Feature Branch**: `practica-guiada-sdd-semana-2`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "Preparar el servicio para ejecutarse en contenedores con una base de datos relacional dedicada, exponer un chequeo real de conectividad, seleccionar el adaptador mediante DATABASE_URL y orquestar los servicios api/db de forma reproducible."

**Contrato observable**: los escenarios E001–E006, los requisitos FR/NFR y los criterios SC describen respuestas REST/CLI y comportamiento de arranque verificable. Las tecnologías citadas son las exigidas por ADR-004 y la Constitución 1.1.0; DTOs, rutas de código y detalles de implementación quedan para el plan.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chequeo real de salud (Priority: P1)

Operaciones necesita confirmar que el servicio y la base configurada están realmente accesibles, desde la web y desde la terminal.

**Why this priority**: sin una señal de salud basada en conectividad real, un contenedor podría aparecer disponible mientras la base está caída.

**Independent Test**: invocar `GET /health` y el comando `health` contra un almacenamiento accesible y, después, contra uno sin conectividad, comparando cuerpo y estado/código de salida.

**Acceptance Scenarios**:

1. **E001 — Given** una base configurada y accesible, **When** se invoca `GET /health` o el comando `health`, **Then** se ejecuta un `SELECT 1` real sobre esa base y se devuelve `{"status":"ok","database":"connected"}` con HTTP 200 en web y código de salida 0 en CLI.
2. **E002 — Given** una base configurada sin conectividad, o un `check_health()` que retorna `False`, **When** se invoca `GET /health` o el comando `health`, **Then** la web responde HTTP 503 con `{"status":"error","database":"unavailable"}` y la CLI devuelve el mismo JSON con código 1, sin éxito falso ni caída a otro almacenamiento.

---

### User Story 2 - Selección transparente del adaptador (Priority: P1)

Plataforma necesita ejecutar la misma aplicación con SQLite en desarrollo y con PostgreSQL en el despliegue dedicado, sin cambiar reglas de negocio.

**Why this priority**: la selección por configuración es la condición para conservar la paridad REST/CLI y las regresiones H001–H003 en ambos entornos.

**Independent Test**: ejecutar el mismo chequeo de salud con `DATABASE_URL` ausente, con `sqlite:///...` y con `postgresql://...`, verificando que la sentencia reachability se dirige al almacenamiento esperado.

**Acceptance Scenarios**:

1. **E003 — Given** `DATABASE_URL` no definida, **When** se inicia el servicio o se ejecuta el comando `health`, **Then** se utiliza SQLite en memoria `sqlite:///:memory:` y el contrato de salud es el de E001 sin configuración adicional.
2. **E004 — Given** `DATABASE_URL` con prefijo `sqlite:///...`, **When** se invoca el chequeo de salud, **Then** se ejecuta `SELECT 1` en ese archivo SQLite y se devuelve el mismo contrato REST/CLI que con PostgreSQL.
3. **E005 — Given** `DATABASE_URL` con prefijo `postgresql://` apuntando a la base del servicio `db`, **When** se invoca el chequeo de salud desde el contenedor `api`, **Then** se ejecuta `SELECT 1` en PostgreSQL y se devuelve el mismo contrato REST/CLI, sin ramas de lógica de negocio por entorno.

---

### User Story 3 - Arranque orquestado y reproducible (Priority: P2)

Plataforma necesita levantar la pila desde cero con la base lista antes que la API y con una señal de salud que refleje la conectividad real.

**Why this priority**: garantiza un despliegue reproducible y evita que la API acepte tráfico antes de que la base dedicada esté disponible.

**Independent Test**: levantar la composición desde un estado limpio y comprobar el orden de readiness y el resultado de `/health` antes y después de que la base esté disponible.

**Acceptance Scenarios**:

1. **E006 — Given** un `Dockerfile` con `uv` y `python:3.12-slim`, un `.dockerignore` y una composición con los servicios `db` y `api`, **When** se levanta la pila desde cero, **Then** `db` usa `postgres:16-alpine` con volumen persistente y healthcheck mediante `pg_isready`; `api` recibe `DATABASE_URL` apuntando a `db`, declara `depends_on` con `service_healthy` y su healthcheck sobre `/health` solo reporta disponibilidad cuando la conectividad es real (E001/E002).

---

### Edge Cases

- Con `DATABASE_URL` ausente se usa memoria efímera: apta para el chequeo de salud, pero no sustituye el almacenamiento persistente exigido por H003 para altas.
- Un valor de `DATABASE_URL` fuera de `postgresql://` o `sqlite:///` se rechaza en la composición; nunca produce un éxito falso ni una caída silenciosa a SQLite.
- Si la conexión falla por red, credenciales o base detenida, el resultado es E002; no se simula éxito ni se consulta otra base.
- El chequeo solo ejecuta `SELECT 1`: no crea, modifica ni elimina datos de incidentes.
- Se conservan sin cambios los contratos y reglas de H001–H003, incluido el criterio de activos de H002 y las políticas de triaje y SLA.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: exponer `GET /health` y el comando `health` de CLI; ambos invocan el mismo caso de uso, que ejecuta un `SELECT 1` real a través de `check_health()` sobre la base configurada.
- **FR-002**: cuando existe conectividad, responder HTTP 200 con `{"status":"ok","database":"connected"}` y hacer que la CLI devuelva el mismo JSON con código de salida 0.
- **FR-003**: cuando `check_health()` retorna `False`, responder HTTP 503 con `{"status":"error","database":"unavailable"}` y hacer que la CLI devuelva el mismo JSON con código de salida 1.
- **FR-004**: seleccionar el adaptador de salida según `DATABASE_URL`: `postgresql://` usa PostgreSQL, `sqlite:///` usa SQLite y, si la variable no existe, se usa `sqlite:///:memory:`. Esta selección no altera casos de uso ni reglas de negocio.
- **FR-005**: incluir un `Dockerfile` basado en `python:3.12-slim` con `uv` y un `.dockerignore` para el contexto de construcción.
- **FR-006**: definir en la composición el servicio `db` con `postgres:16-alpine`, volumen persistente y healthcheck con `pg_isready`, y el servicio `api` con `DATABASE_URL` apuntando a `db`, `depends_on` con `service_healthy` y healthcheck sobre `/health`.
- **FR-007**: conservar todos los endpoints, comandos, respuestas, paridad REST/CLI y reglas de negocio de H001–H003; este hito solo añade salud y runtime.

### Non-Functional Requirements

- **NFR-001**: la señal de salud debe provenir de conectividad real, nunca de una respuesta estática, caché o comprobación que no llegue a la base configurada.
- **NFR-002**: mantener la frontera hexagonal: dominio y aplicación sin HTTP, CLI, drivers ni ORM; REST y CLI delegan en el mismo caso de uso y la selección de persistencia queda confinada a la composición de salida.
- **NFR-003**: conservar timestamps como texto ISO 8601 en ambos motores, además del filtrado parametrizado, JOIN, índice compuesto y reglas de triaje/SLA vigentes.
- **NFR-004**: las pruebas automatizadas usan SQLite en memoria o archivos temporales aislados, sin servicios externos ni datos reales; la verificación con PostgreSQL se documenta como evidencia de la composición.
- **NFR-005**: las versiones `python:3.12-slim` y `postgres:16-alpine` quedan declaradas para que la pila sea reproducible desde un estado limpio.

### Key Entities *(include if feature involves data)*

- **Resultado de salud**: par observable `status`/`database` con dos formas exactas: conectado o no disponible; equivale al valor booleano de `check_health()`.
- **Configuración de persistencia**: `DATABASE_URL` con dos prefijos admitidos y valor predeterminado en memoria; determina el destino del `SELECT 1`.
- **Entorno orquestado**: servicios `api` y `db`, volumen persistente de la base y dos healthchecks con dependencia de arranque.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: los seis escenarios E001–E006 pasan con trazabilidad a pruebas de aceptación `test_bdd_*`, incluidos éxito, fallo y las tres variantes de configuración.
- **SC-002**: el 100% de los chequeos contra una base accesible devuelve el cuerpo de éxito con HTTP 200/CLI 0, y el 100% de los chequeos sin conectividad devuelve el cuerpo de error con HTTP 503/CLI 1.
- **SC-003**: en 3 de 3 variantes (`DATABASE_URL` ausente, SQLite y PostgreSQL) se selecciona el destino esperado y el contrato observable de salud es idéntico.
- **SC-004**: en dos arranques consecutivos desde cero, la base alcanza su estado saludable antes de que la API inicie y el healthcheck de la API solo pasa cuando la conectividad es real.
- **SC-005**: el 100% de las regresiones de H001–H003 continúa pasando, sin eliminar ni debilitar pruebas existentes.
- **SC-006**: el 100% de las pruebas automatizadas usa almacenamiento aislado y ninguna emplea datos de producción.

## Assumptions

- La CLI usa el mismo JSON que REST para salud y los códigos 0/1 ya empleados por H002 y H003; no se define un formato de error distinto.
- Los valores de credenciales, nombre de base y nombre del volumen son parámetros de despliegue del plan, no funcionalidades nuevas.
- Un `DATABASE_URL` con esquema no soportado conserva el comportamiento actual de error de configuración; no se añade un tercer motor ni un fallback.
- La verificación BDD de salud se ejecuta con SQLite aislado; el camino PostgreSQL se evidencia en la composición, sin datos reales ni servicios externos en pytest.
- No se añaden endpoints, comandos, autenticación, migraciones ni monitorización adicional a lo solicitado.
