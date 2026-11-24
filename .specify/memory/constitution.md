# Constitución de IncidentOps

## Core Principles

### I. Dominio determinista único
Las entidades, reglas de triaje y cálculo SLA residen en src/domain/ (models.py,
triage_rules.py y sla_calculator.py). Ninguna capa externa duplica estas reglas.
La urgencia subjetiva no eleva por sí sola la severidad. Las claves de correlación
identifican candidatos a duplicados, no confirman causa raíz. Los equipos válidos
son Backend-Core, Platform-SRE, Data-DBA y Security-IAM.

### II. Arquitectura hexagonal estricta (ADR-003)
El dominio importa únicamente stdlib y módulos propios. La aplicación importa
stdlib, dominio y módulos propios; define casos de uso en services.py y puertos
secundarios mediante typing.Protocol en ports.py cuando exista persistencia.
Los adaptadores de entrada REST y CLI delegan en IncidentService; no importan
drivers ni repositorios concretos. La composición usa la fábrica de adaptadores
de salida. Los adaptadores de salida implementan los puertos y se seleccionan
mediante DATABASE_URL. MCP es una extensión futura, no un requisito actual.

### III. Políticas de SLA y estados
P0: 60 min; P1: 240 min, ambos 24/7. P2: 480 min; P3: 1440 min, ambos
L-V [08:00, 18:00), sin festivos configurados. Incumplimiento si los minutos
completos exceden el límite; escalamiento desde el 75% exacto, incluso después
del vencimiento mientras no se resuelva. RESOLVED usa resolved_at, conserva
incumplimiento histórico y no escala. Se respetan las reglas de fechas de ADR-002.
Estados: OPEN, IN_PROGRESS, ESCALATION_REQUIRED y RESOLVED; H002 consulta
exclusivamente OPEN e IN_PROGRESS.

### IV. Paridad y aceptación verificable
REST y CLI MUST compartir el mismo caso de uso y resultados equivalentes.
Cada especificación MUST expresar escenarios Given / When / Then en lenguaje de
negocio, con pruebas de aceptación pytest trazables y almacenamiento aislado
cuando corresponda. Se conservan las regresiones de hitos anteriores.

### V. Calidad y simplicidad
Python >=3.10 gestionado con uv. REST usa FastAPI y Pydantic v2; CLI usa Typer.
SQLite3 estándar, sin ORM pesado (ADR-001); cualquier cambio de motor requiere
un ADR previo. No incorporar funcionalidades de hitos futuros. Ruff MUST validar
las fronteras de imports desde H002; pytest MUST verificar aceptación y regresión.

## Restricciones técnicas

El dominio y la aplicación no dependen de HTTP, CLI, SQLite ni otros frameworks.
Los adaptadores secundarios son intercambiables; SQLite filtra en SQL mediante
consultas parametrizadas, JOIN e índice compuesto según ADR-001. Las políticas
de SLA permanecen en el dominio. Las pruebas no dependen de servicios externos.

## Flujo de desarrollo y puertas de calidad

Antes de implementar: especificar, clarificar, planificar, desglosar tareas,
analizar consistencia y obtener aprobación humana. Verificar mediante
uv run ruff check src/ y uv run pytest -v; conservar evidencia real de resultados.
AGENTS.md mantiene el manual operativo; ROADMAP.md expresa visión de producto;
las especificaciones son contratos funcionales; ADRs registran decisiones
estructurales. No afirmar que un comando o prueba se ejecutó sin evidencia.

## Governance

Esta Constitución rige los hitos a partir de su ratificación. Las enmiendas
requieren revisión humana, justificación, fecha y versión semántica:
MAJOR para cambios incompatibles; MINOR para nuevos principios o ampliaciones;
PATCH para aclaraciones. Los ADR aceptados se preservan y se reemplazan mediante
otro ADR si cambia la decisión. Cada plan y revisión debe comprobar el cumplimiento
de estos principios; una desviación requiere aprobación y registro explícitos.

**Version**: 1.0.0 | **Ratified**: 2026-11-24 | **Last Amended**: 2026-11-24
