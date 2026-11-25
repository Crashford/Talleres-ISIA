<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.1.0
- Modified principles:
  - II. Arquitectura hexagonal estricta (ADR-003) → II. Arquitectura hexagonal estricta (ADR-003, ADR-004)
  - V. Calidad y simplicidad → V. Calidad y simplicidad (sin ORM; psycopg[binary] en salida)
  - Restricciones técnicas → Restricciones técnicas (persistencia dual y puertos)
- Added sections: VI. Persistencia dual y paridad temporal; VII. Despliegue reproducible en contenedores
- Removed sections: none
- Follow-up TODOs: none
-->

# Constitución de IncidentOps

## Core Principles

### I. Dominio determinista único
Las entidades, reglas de triaje y cálculo SLA residen en el dominio (modelos,
triaje y calculadora). Ninguna capa externa duplica estas reglas. La urgencia
subjetiva no eleva por sí sola la severidad. Las claves de correlación
identifican candidatos a duplicados, no confirman causa raíz. Los equipos válidos
son Backend-Core, Platform-SRE, Data-DBA y Security-IAM.

### II. Arquitectura hexagonal estricta (ADR-003, ADR-004)
El dominio y la aplicación importan únicamente stdlib y módulos propios: no
dependen de HTTP, CLI, drivers ni de infraestructura. La aplicación define los
casos de uso en IncidentService y el puerto secundario IncidentRepositoryPort
con typing.Protocol. Los adaptadores de entrada REST y CLI delegan en el mismo
caso de uso y no importan repositorios concretos. La composición selecciona el
adaptador de salida mediante DATABASE_URL. MCP es una extensión futura, no un
requisito actual.

### III. Políticas de SLA y estados
P0: 60 min; P1: 240 min, ambos 24/7. P2: 480 min; P3: 1440 min, ambos
L-V [08:00, 18:00), sin festivos configurados. Incumplimiento si los minutos
completos exceden el límite; escalamiento desde el 75% exacto, incluso después
del vencimiento mientras no se resuelva. RESOLVED usa resolved_at, conserva el
incumplimiento histórico y no escala. Se respetan las reglas de fechas de ADR-002.
Estados: OPEN, IN_PROGRESS, ESCALATION_REQUIRED y RESOLVED; H002 consulta
exclusivamente OPEN e IN_PROGRESS.

### IV. Paridad y aceptación verificable
REST y CLI MUST compartir el mismo caso de uso y resultados equivalentes. Cada
especificación MUST expresar escenarios Given / When / Then en lenguaje de
negocio, con pruebas de aceptación pytest trazables y almacenamiento aislado
cuando corresponda. Se conservan las regresiones de hitos anteriores.

### V. Calidad y simplicidad
Python >=3.10 gestionado con uv. REST usa FastAPI y Pydantic v2; CLI usa Typer.
El sistema no usa ORM: SQLite3 estándar para desarrollo local y pruebas, y
PostgreSQL con el driver psycopg[binary] en el adaptador de salida (ADR-004).
Ruff MUST validar las fronteras de imports; pytest MUST verificar aceptación y
regresiones. No incorporar funcionalidades de hitos futuros sin aprobación.

### VI. Persistencia dual y paridad temporal (ADR-004)
La persistencia MUST implementar IncidentRepositoryPort con dos adaptadores:
sqlite3 para desarrollo local y pruebas, y psycopg[binary] para PostgreSQL.
DATABASE_URL MUST seleccionar el adaptador; si está ausente, MUST resolver a
SQLite en memoria `sqlite:///:memory:`. Los timestamps MUST almacenarse como
TEXT en ISO 8601 en ambos motores para garantizar paridad temporal. El filtrado
SQL parametrizado, el JOIN y el índice compuesto de ADR-001 se conservan en el
adaptador SQLite.

### VII. Despliegue reproducible en contenedores (ADR-004)
Docker Compose MUST definir los servicios `api` y `db`; `db` MUST usar la imagen
`postgres:16-alpine`. La misma aplicación MUST operar con SQLite local o con
PostgreSQL según DATABASE_URL, sin ramas de lógica de negocio por entorno.

## Restricciones técnicas

La frontera hexagonal es obligatoria: el núcleo no conoce SQLite, PostgreSQL,
HTTP, CLI ni ORMs. Las reglas de triaje y las políticas de SLA permanecen en el
dominio. Las pruebas NO deben depender de servicios externos: usan SQLite en
memoria o un repositorio aislado. Un cambio de motor o de driver requiere un ADR
previo; ADR-001 se conserva para SQLite y ADR-004 rige el despliegue dual.

## Flujo de desarrollo y puertas de calidad

Antes de implementar: especificar, clarificar, planificar, desglosar tareas,
analizar consistencia y obtener aprobación humana. Cada especificación MUST
expresar escenarios Given / When / Then y pruebas pytest trazables, con paridad
REST/CLI y almacenamiento aislado. Verificar mediante `uv run ruff check src/` y
`uv run pytest -v`; conservar evidencia real de resultados. AGENTS.md mantiene el
manual operativo; ROADMAP.md expresa visión de producto; los ADR registran
decisiones estructurales inmutables. No afirmar resultados sin evidencia.

## Governance

Esta Constitución rige los hitos a partir de su ratificación. Las enmiendas
requieren revisión humana, justificación, fecha y versión semántica: MAJOR para
eliminación o redefinición incompatible de principios; MINOR para principios o
secciones nuevas y ampliaciones materiales; PATCH para aclaraciones y ajustes no
semánticos. Los ADR aceptados se preservan; si una decisión cambia, se emite otro
ADR. Cada plan y revisión MUST comprobar el cumplimiento de estos principios; una
desviación requiere aprobación y registro explícitos.

**Version**: 1.1.0 | **Ratified**: 2026-11-24 | **Last Amended**: 2026-11-24
