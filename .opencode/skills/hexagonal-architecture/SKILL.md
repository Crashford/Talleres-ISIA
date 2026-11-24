---
name: hexagonal-architecture
description: Aplica las fronteras hexagonales de IncidentOps al diseñar, modificar o revisar dominio, casos de uso, puertos y adaptadores; verifica imports y paridad REST/CLI.
---

# Arquitectura hexagonal

1. Leer la Constitución oficial y ADR-001, ADR-002 y ADR-003 antes de diseñar.
2. `src/domain/`: exclusivamente stdlib y módulos propios; prohibidos HTTP, CLI, drivers, ORM, aplicación y adaptadores.
3. `src/application/`: stdlib, dominio y módulos propios. Definir puertos con `typing.Protocol`; casos de uso en IncidentService. No importar adaptadores ni frameworks.
4. `src/adapters/inbound/`: convertir entrada/salida y delegar en IncidentService; no importar SQLite, drivers, ORM ni repositorios concretos. Para componer persistencia, usar `src.adapters.outbound.factory`.
5. `src/adapters/outbound/`: implementar IncidentRepositoryPort; encapsular SQL, conexiones y configuración DATABASE_URL. Mantener reglas de SLA y triaje en dominio.
6. REST y CLI deben invocar el mismo caso de uso; no duplicar validaciones de negocio, clasificación, filtrado funcional ni cálculo SLA.
7. Configurar Ruff con E4, E7, E9, F y TID en pyproject.toml y archivos ruff.toml jerárquicos en domain, application e inbound. Usar TID251 (banned-api) y TID252 (ban-relative-imports = "parents") en las fronteras; permitir el import explícito de la fábrica de salida en inbound sin permitir repositorios concretos.
8. Ejecutar `uv run ruff check src/` y `uv run pytest -v`. Revisar también imports de terceros no cubiertos por la lista de prohibiciones. Corregir infracciones; no suprimirlas sin justificación y aprobación.
