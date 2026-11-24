# Data Model — H002

- **Incident** (existente): incident_id, title, component, severity, status, created_at, resolved_at opcional. No cambiar semántica.
- **SLARule / SLAEvaluation** (existentes): única fuente de política y cálculo en dominio.
- **ActiveIncidentItem** (DTO): incident_id, title, component, severity, status, elapsed_minutes, is_breached, requires_escalation.
- **ActiveIncidentsSummary** (DTO): total_active, breached_count, incidents (lista de items). Los conteos derivan de la misma colección.
- **Persistencia**: tabla incidents existente con clave de correlación nullable para el puerto, tabla sla_policies derivada del dominio, índice compuesto (component,status). La consulta activa hace INNER JOIN por severity y devuelve entidades. Una clave nula no es candidata a duplicado; la función de triaje no persiste nada. El dominio calcula los minutos y las alertas, no SQL.
