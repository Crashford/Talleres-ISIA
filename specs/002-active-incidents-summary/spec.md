# Feature Specification: H002 — Resumen de incidentes activos

**Feature Branch**: `practica-guiada-sdd-semana-2` | **Created**: 2026-11-24 | **Status**: Clarificada según guía §2.3, pendiente de aprobación del plan

**Input**: Operaciones necesita consultar desde web y terminal los incidentes activos (OPEN e IN_PROGRESS), total activo, incumplimientos de SLA, detalle y filtro opcional por componente.

## User Scenarios & Testing *(mandatory)*

### US1 — Consultar el resumen global (P1)
Operaciones necesita saber cuántos incidentes están activos y fuera de SLA, sin confundirlos con casos cerrados.

**Independent Test**: preparar incidentes activos y no activos; consultar con un tiempo de referencia fijo y comprobar los totales y detalles.

- **E001 — Given** dos incidentes activos (OPEN e IN_PROGRESS), uno resuelto y uno en estado ESCALATION_REQUIRED, **When** Operaciones consulta el resumen global en un instante de referencia fijado, **Then** obtiene solo los dos activos, el total de 2, el número de incumplidos calculado según su SLA y el detalle de ambos, incluyendo la necesidad de escalamiento.

### US2 — Filtrar y consultar ausencia de incidentes (P2)
Operaciones necesita concentrarse en un componente sin alterar las reglas de SLA.

**Independent Test**: consultar un componente con coincidencias y otro sin coincidencias.

- **E002 — Given** incidentes activos de distintos componentes, **When** se solicita el resumen de uno de ellos, **Then** los totales y el detalle corresponden exclusivamente a dicho componente.
- **E003 — Given** que no existen incidentes activos o no hay coincidencias para el componente, **When** se consulta el resumen, **Then** la consulta es exitosa y devuelve cero activos, cero incumplidos y una colección vacía.

### US3 — Consultar desde terminal (P3)
Soporte necesita el mismo resultado sin usar la interfaz web.

**Independent Test**: consultar el mismo almacenamiento y tiempo de referencia en ambas interfaces.

- **E004 — Given** el mismo conjunto de incidentes, filtro e instante de referencia, **When** Soporte consulta desde terminal, **Then** recibe un resultado JSON válido equivalente al de la consulta web.

### Edge Cases

- RESOLVED y ESCALATION_REQUIRED no forman parte del resumen: la definición de activo del H002 es estrictamente OPEN o IN_PROGRESS.
- Una consulta sin coincidencias no constituye un error.
- El tiempo de referencia permite repetir la evaluación SLA, no reconstruir el historial de estados. Se conservan las reglas de fechas de ADR-002.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: devolver exclusivamente incidentes OPEN e IN_PROGRESS.
- **FR-002**: devolver total de activos y número de incumplimientos de SLA sobre el mismo conjunto.
- **FR-003**: por cada incidente, devolver identificador, título, componente, severidad, estado, minutos transcurridos, si incumplió su SLA y si requiere escalamiento, según el dominio existente.
- **FR-004**: permitir filtro opcional por componente, aplicable tanto a totales como a detalle.
- **FR-005**: permitir tiempo de referencia opcional; si se omite, evaluar al instante actual.
- **FR-006**: devolver una respuesta exitosa con totales cero y lista vacía si no hay coincidencias.
- **FR-007**: proporcionar resultados equivalentes por web y terminal para el mismo conjunto, filtro y tiempo de referencia.

### Key Entities

- Incidente: identificador, título, componente, severidad, estado y fecha de creación.
- Resumen: total activo, número de incumplidos y detalle de incidentes con evaluación SLA.

## Success Criteria *(mandatory)*

- **SC-001**: los cuatro escenarios E001–E004 pasan sus pruebas automatizadas.
- **SC-002**: ningún incidente fuera de los dos estados activos aparece en resultados; el conteo de incumplidos coincide con el detalle.
- **SC-003**: ambas interfaces devuelven resultados equivalentes ante las mismas entradas.
- **SC-004**: las pruebas de aceptación y regresión H001 continúan pasando.

## Assumptions

Consulta de solo lectura; sin creación, cierre, cambios de estado, historial, detección persistente de duplicados por interfaz ni nuevo motor de almacenamiento. Los datos existentes o de prueba se suministran al repositorio; no se generan incidentes automáticamente durante una consulta.

## Clarifications — 2026-11-24

Decisiones expresas de la guía (página 13):
- GET /api/v1/incidents/summary, con query parameter opcional component.
- CLI summary [--component ...] [--reference-time ...].
- reference_time opcional en ambas interfaces, por defecto instante actual.
- Respuesta exitosa HTTP 200 / JSON válido: total_active=0, breached_count=0, incidents=[] cuando no existen coincidencias.
- Se mantienen los cuatro escenarios BDD anteriores. Los detalles técnicos adicionales (formato de fechas, manejo de entradas inválidas y orden) se someten a aprobación en el plan.
