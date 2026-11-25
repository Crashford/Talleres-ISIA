# Roadmap de producto y operaciones — IncidentOps

| Hito | Resultado de negocio | Estado |
|---|---|---|
| H001 — Triaje multi-interfaz | Exponer la clasificación y el enrutamiento determinista de reportes sin persistencia, para consumo inmediato desde web y terminal. | Cerrado; evidencia en `evidence/H001-verificacion.md`. |
| H002 — Resumen de incidentes activos | Consultar incidentes actualmente activos, incumplimientos de SLA y filtrado por componente desde web y terminal. | Cerrado; evidencia en `evidence/H002-verificacion.md`. |
| H003 — Ciclo de vida, duplicados y SLA | Registrar incidentes entrantes de forma persistente, alertar si existe otro equivalente abierto y auditar su SLA en cualquier instante de referencia. | Cerrado; evidencia en `evidence/H003-manual.md`, `evidence/H003-verificacion.md` y regresiones conservadas. |
| H004 — Persistencia relacional dedicada y runtime en contenedores | Preparar la ejecución reproducible en contenedores con base de datos relacional dedicada y chequeo real de conectividad operativa. | Cerrado; dos arranques consecutivos, `api` y `db` healthy, `/health` HTTP 200, 96 pruebas y 10 subpruebas. Evidencia en `evidence/H004-verify.md`. |

## Cierre del taller autónomo

Fecha: 2026-11-24. H003 y H004 quedan cerrados con evidencia real. H004 conserva el registro del fallo de integración, su causa raíz en el ciclo de vida de la conexión PostgreSQL, las regresiones añadidas y la validación real de Docker Compose con volumen persistido. No se modificaron reglas de negocio, Constitución, ADR, credenciales ni dependencias durante el cierre documental.
