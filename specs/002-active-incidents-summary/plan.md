# Implementation Plan: H002 — Resumen de incidentes activos

**Branch**: `practica-guiada-sdd-semana-2` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Status**: Aprobado e implementado; ver evidence/H002-verificacion.md.

## Summary

Consultar activos y SLA por REST y CLI mediante IncidentService; extraer persistencia SQLite optimizada a un adaptador secundario. Mantener el triaje H001 stateless.

## Technical Context

- **Language/Version**: Python >=3.10, uv.
- **Primary Dependencies**: FastAPI, Pydantic v2, Typer; Ruff, pytest, httpx de desarrollo.
- **Storage**: SQLite3 stdlib; DATABASE_URL, por defecto sqlite:///:memory:.
- **Testing**: pytest, TestClient, CliRunner, bases aisladas y Ruff.
- **Target Platform**: backend y terminal multiplataforma.
- **Project Type**: proyecto Python único, REST + CLI.
- **Performance Goals**: eliminar N+1 y escaneo completo en Python; medir benchmark heredado de 10.000 registros, sin inventar umbral de latencia.
- **Constraints**: ADR-001/002/003; sin ORM pesado, sin H003/H004 ni nuevas rutas de escritura.
- **Scale/Scope**: resumen de activos, filtro opcional y evaluación SLA reproducible.

## Constitution Check

| Principio | Diseño previsto |
|---|---|
| I — Dominio único | evaluate_sla_status permanece en dominio; sin duplicar políticas. |
| II — Hexagonal | Protocol en aplicación; SQLite implementa puerto; fábrica como único punto de composición desde entrada. |
| III — SLA y estados | OPEN/IN_PROGRESS exclusivamente; mantener umbrales, calendario y validaciones heredadas. |
| IV — Paridad y BDD | Mismo servicio y JSON, referencia fija en pruebas, cobertura E001–E004 y regresiones. |
| V — Calidad | Ruff jerárquico, pytest y uv; persistencia SQLite parametrizada. |

**Gate de diseño**: conforme; decisiones aprobadas por el usuario y verificación Ruff/pytest exitosa en CI.

## Project Structure

```text
specs/002-active-incidents-summary/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/summary.md
├── quickstart.md
├── tasks.md
└── checklists/requirements.md
src/
├── domain/
│   ├── models.py
│   └── ruff.toml
├── application/
│   ├── ports.py
│   ├── services.py
│   └── ruff.toml
├── adapters/
│   ├── inbound/
│   │   ├── api/{app,schemas}.py
│   │   ├── cli.py
│   │   └── ruff.toml
│   └── outbound/
│       ├── sqlite_repository.py
│       └── factory.py
└── incident_repository.py (benchmark heredado, delegando en el nuevo adaptador)
tests/
├── conftest.py
├── test_spec_001_triage.py
└── test_spec_002_summary.py
```

**Structure Decision**: conservar proyecto único, añadir puertos secundarios y composición bajo adaptadores. No crear servicios paralelos ni otro motor.

## Diseño técnico

1. Puerto runtime-checkable IncidentRepositoryPort: save_incident(incident, duplicate_group_key=None), get_incident(incident_id), find_open_duplicates(duplicate_group_key), list_active_incidents(component_filter=None), check_health(). Tipos del dominio; sin dependencias de almacenamiento.
2. SQLiteIncidentRepository: extraer esquema heredado y semilla para benchmark; INNER JOIN sla_policies y WHERE status IN ('OPEN','IN_PROGRESS') con filtro opcional parametrizado e índice (component,status). Mantener políticas de SLA como fuente del dominio. Agregar columna nullable de correlación de forma compatible para el puerto (sin exponer detección por REST/CLI); conservar datos previos.
3. factory.py interpreta DATABASE_URL para SQLite y abre/cierra repositorios por operación; rutas relativas/absolutas y :memory:, rechazar motores no aprobados. Inyección de fábrica para pruebas. H001 no abre base.
4. IncidentService.get_active_incidents_summary(component_filter, reference_time) obtiene los activos por puerto, evalúa SLA una vez por incidente mediante dominio, calcula totales y DTOs independientes del framework. Validar referencia temporal y ordenar resultados por incident_id para paridad.
5. Adaptadores: ampliar schemas.py con ActiveIncidentItem y ActiveIncidentsSummaryResponse, agregar GET y subcomando summary según [contrato](contracts/summary.md). Validación de negocio compartida; HTTP 422 y CLI 1 ante entradas inválidas.
6. Ruff: [tool.ruff.lint] select = ["E4","E7","E9","F","TID"]; archivos ruff.toml por capa con extend relativo a pyproject.toml, banned-api TID251 y ban-relative-imports = "parents" TID252. Prohibir imports de capas externas/frameworks/drivers en dominio/aplicación, e imports de SQLite y repositorios concretos en inbound (permitir factory). Revisar manualmente imports no cubiertos por la lista.
7. Tests: cuatro funciones BDD trazadas a E001–E004, pruebas de puerto con SQLite, esquema/índice y consultas, validación de fechas y regresiones. CI: ejecutar Ruff, pytest, motores de dominio, CLI triage/summary y benchmark. Documentar salida real.

## Complexity Tracking

Sin desviaciones previstas de la Constitución. No se agrega dependencia de ejecución ni se introduce un motor de BD adicional.
