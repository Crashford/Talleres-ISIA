# Constitución manual de IncidentOps

## I. Dominio determinista único
- Triaje, severidades, equipos y claves de correlación se definen únicamente en el dominio. La urgencia subjetiva no eleva por sí sola la severidad; las claves de duplicados identifican candidatos, no prueban causa raíz.
- Equipos válidos: Backend-Core, Platform-SRE, Data-DBA, Security-IAM. Estados heredados: OPEN, IN_PROGRESS, ESCALATION_REQUIRED, RESOLVED. H002 consulta exclusivamente OPEN e IN_PROGRESS.
- SLA: P0 60 min y P1 240 min en 24/7; P2 480 min y P3 1440 min de lunes a viernes [08:00, 18:00), sin festivos configurados. Incumplimiento cuando los minutos completos exceden el límite; escalamiento desde el 75% exacto, incluso tras vencer mientras no se resuelva. Para RESOLVED se usa resolved_at y no se escala. Conservar las reglas de fechas y zona local de ADR-002.

## II. Arquitectura hexagonal (ADR-003)
- src/domain/: modelos, triaje y SLA; únicamente biblioteca estándar y módulos del dominio.
- src/application/: casos de uso compartidos en IncidentService y puertos secundarios mediante typing.Protocol; únicamente stdlib y dominio, además de módulos propios.
- src/adapters/inbound/: REST y CLI delegan en IncidentService; no duplican lógica ni importan drivers o repositorios concretos. La composición usa una fábrica de adaptadores secundarios cuando se requiera persistencia.
- src/adapters/outbound/: implementaciones de puertos, intercambiables; el núcleo no conoce adaptadores. MCP es una posibilidad futura.

## III. Gobernanza técnica y calidad
- Python >=3.10 gestionado con uv; FastAPI y Pydantic v2 para REST; Typer para CLI; SQLite3 estándar sin ORM pesado (ADR-001). Otro motor requiere ADR previo.
- Antes del código: especificar comportamiento en BDD Given / When / Then, aclarar contratos y aprobar plan. Pruebas de aceptación automatizadas con pytest y regresiones del núcleo; paridad REST/CLI. No declarar pruebas ejecutadas sin evidencia.
- Los ADR aceptados son históricos: si una decisión cambia, emitir otro ADR. AGENTS.md es operativo; ROADMAP.md expresa hitos; especificaciones y planes no sustituyen a esta Constitución.
