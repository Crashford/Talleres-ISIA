# H001 — Triaje multi-interfaz (SDD manual)

## Objetivo y alcance

Permitir que frontend y soporte clasifiquen y enruten un reporte inmediatamente desde web y terminal, con idéntico resultado determinista y sin persistir incidentes. El registro y ciclo de vida quedan fuera del alcance.

## Contrato acordado según la práctica guiada, §1.3

- HTTP: POST /api/v1/incidents/triage, cuerpo JSON con incident_id y raw_text de tipo string. Éxito: 200 OK con todos los campos de TriageResult (incident_id, severity, component, rationale, consistency_ratio, recommended_team, duplicate_group_key). Campos vacíos o compuestos solo por espacios tras strip(), ausentes o de tipo incorrecto: 422.
- CLI: triage --incident-id ... --raw-text ...; mismo resultado JSON en stdout y código de salida 0. Entradas vacías o compuestas solo por espacios: mensaje de error y código 1.
- Operación stateless. Ambas interfaces delegan en el mismo caso de uso IncidentService.triage_incident; no realizan escritura ni consultan la base de datos.
- La clave canónica de correlación de fallos HTTP 502 de pagos será payments-gateway:http-502-outage, en sustitución de payments-gateway:http-502-card-payments del módulo heredado. La clasificación y agrupación restante no cambian.

## Escenarios de aceptación BDD

### E001 — Caída crítica de pagos por HTTP 502
**Given** un reporte INC-1001 con texto «HTTP 502 Bad Gateway en pasarela de pagos».

**When** el frontend solicita su triaje.

**Then** recibe 200 y la clasificación P0, componente payments-gateway, equipo Backend-Core y clave payments-gateway:http-502-outage, junto con los demás campos del resultado.

### E002 — Bloqueo individual con urgencia subjetiva
**Given** un reporte INC-1002 con texto «URGENTE hoy: mi cuenta está bloqueada».

**When** se solicita su triaje por web.

**Then** recibe 200 con severidad P2 y equipo Security-IAM; la palabra «hoy» no genera un falso positivo P0.

### E003 — Datos de entrada vacíos
**Given** un reporte sin identificador válido o sin texto significativo (cadena vacía o únicamente espacios).

**When** se solicita el triaje por web.

**Then** se rechaza la solicitud con 422, sin clasificación ni persistencia.

### E004 — Paridad desde terminal
**Given** el mismo reporte de caída de pagos del escenario E001.

**When** soporte ejecuta triage --incident-id INC-1001 --raw-text "HTTP 502 Bad Gateway en pasarela de pagos".

**Then** obtiene código 0 y JSON válido en stdout, con P0, Backend-Core y todos los mismos valores que por web.

## Criterios complementarios

- E005: una entrada CLI vacía o solo espacios se rechaza con código 1, sin emitir un resultado de triaje.
- Conservar las pruebas de regresión de la Semana 1; actualizar únicamente expectativas incompatibles con la nueva clave canónica, si existen.
- No incluir nuevas reglas de clasificación, gestión de duplicados persistentes, resumen de incidentes ni nuevos adaptadores en H001.
