# Feature Specification: H003 — Ciclo de vida, duplicados y SLA

**Feature Branch**: `practica-guiada-sdd-semana-2` | **Created**: 2026-11-24 | **Status**: Draft — decisiones A1–A3, T1–T6 y Q1–Q3 incorporadas; sin planificación

**Input**: Operaciones necesita guardar los incidentes cuando llegan, avisar si ya existe otro equivalente abierto y consultar cómo va su SLA desde la web y desde la terminal.

## User Scenarios & Testing *(mandatory)*

### US1 — Registrar el incidente entrante (P1)

Operaciones necesita que cada reporte que llega quede guardado y clasificado de inmediato.

**Independent Test**: registrar un reporte con título y texto válidos mediante la web y la terminal, y comprobar la respuesta y la consulta posterior.

- **E001 — Given** un título y un texto sin clasificar, ambos no vacíos, **When** se envía `POST /api/v1/incidents` o el comando `create` de CLI, **Then** se guarda con identificador autogenerado `INC-HEX8`, fecha de creación actual y estado OPEN, la web responde 201 Created y la CLI devuelve JSON equivalente, con la clasificación completa, `is_duplicate` en falso y `duplicate_of` vacío cuando no hay candidatos.
- **E002 — Given** un título o texto vacío o formado solo por espacios, **When** se intenta registrar, **Then** la web responde 422 y la CLI termina con código de salida 1, sin guardar ningún incidente.
- **E011 — Given** un incidente ya registrado con un identificador concreto, **When** se intenta registrar otro reporte con ese mismo `incident_id`, **Then** la web responde 422 y la CLI termina con código 1, y el incidente existente permanece sin cambios.
- **E013 — Given** un intento de registro con `status` RESOLVED, **When** se envía `POST /api/v1/incidents` o el comando `create` de CLI, **Then** la web responde 422 y la CLI termina con código 1, sin guardar el incidente.
- **E014 — Given** los mismos datos de entrada, `incident_id` y `created_at` en almacenamientos aislados equivalentes, **When** se registra mediante `POST /api/v1/incidents` y mediante CLI `create`, **Then** ambas respuestas contienen el mismo identificador, fecha de creación, clasificación, `is_duplicate` y `duplicate_of`.

### US2 — Avisar de equivalentes abiertos (P1)

Operaciones necesita detectar posibles duplicados en el momento del alta, sin perder el reporte entrante.

**Independent Test**: registrar un reporte cuya `duplicate_group_key` coincide con la de un incidente en estado abierto y comprobar el aviso; repetir sin esa coincidencia.

- **E003 — Given** otro incidente en OPEN, IN_PROGRESS o ESCALATION_REQUIRED con la misma `duplicate_group_key` exacta, **When** se registra el nuevo reporte, **Then** se guarda igualmente y la respuesta marca `is_duplicate` en verdadero y lista en `duplicate_of` los identificadores de esos incidentes, excluido el propio, sin afirmar causa raíz compartida.
- **E004 — Given** que el único incidente con esa clave está RESOLVED o que ningún incidente coincide con la clave calculada, **When** se registra, **Then** el incidente se guarda con `is_duplicate` en falso y `duplicate_of` vacío.

### US3 — Auditar el SLA desde ambas interfaces (P2)

Operaciones y Soporte necesitan saber en cualquier instante cómo va el SLA de un incidente, con el mismo resultado en web y terminal.

**Independent Test**: fijar un instante de referencia, consultar el mismo incidente en ambas interfaces y comparar el resultado.

- **E005 — Given** un incidente guardado con fecha de creación conocida, **When** se consulta `GET /api/v1/incidents/{incident_id}/sla` o el comando `sla` de CLI con un `reference_time` ISO 8601 opcional, **Then** se muestran minutos transcurridos, permitidos y restantes, si incumplió y si requiere escalamiento, según la política de SLA vigente.
- **E006 — Given** un incidente P2 creado el viernes 2026-11-06T17:00:00 y consultado con `reference_time` 2026-11-09T09:00:00, **When** se audita su SLA, **Then** `elapsed_minutes`=120, `allowed_minutes`=480, `remaining_minutes`=360, `is_breached`=false y `requires_escalation`=false.
- **E007 — Given** un incidente resuelto procedente de datos existentes, **When** se consulta su SLA en cualquier instante posterior, **Then** el cálculo usa la fecha de resolución, conserva el incumplimiento histórico y no pide escalamiento.
- **E008 — Given** el mismo incidente guardado y el mismo `reference_time`, **When** se consulta por web y por terminal, **Then** ambas interfaces devuelven el mismo resultado.
- **E009 — Given** un identificador de incidente que no existe, **When** se consulta su SLA por web o por terminal, **Then** la web responde 404 y la CLI termina con código 1, con una explicación clara.
- **E010 — Given** un `reference_time` con formato inválido o anterior a `created_at`, **When** se consulta el SLA, **Then** la web responde 422 y la CLI termina con código 1, sin devolver un cálculo engañoso.
- **E012 — Given** un incidente con `created_at` aware y `reference_time` naive, o con `created_at` naive y `reference_time` aware, o dos marcas aware con offsets distintos en P2/P3, **When** se consulta el SLA, **Then** la web responde 422 y la CLI termina con código 1, sin devolver un cálculo; si `reference_time` se omite, se usa un instante actual compatible con la convención temporal del incidente almacenado.

### Edge Cases

- Si se omite `incident_id`, se autogenera con formato `INC-HEX8`; si se proporciona uno ya existente, se rechaza con 422 o código 1 sin sobrescribir el registro.
- Para el aviso se excluyen los incidentes RESOLVED y el identificador recién creado; el criterio de incidentes activos del Hito 002 (OPEN e IN_PROGRESS) no se modifica.
- El incumplimiento se produce solo cuando los minutos completos exceden el límite; el escalamiento empieza en el 75% exacto y se mantiene tras el vencimiento mientras no se resuelva.
- No hay festivos configurados. Se rechazan con 422 o código 1 las mezclas naive/aware en cualquier orden y, para P2/P3, los offsets distintos entre `created_at` y `reference_time`; sin referencia explícita se usa un instante actual compatible con el incidente almacenado.
- El registro con estado RESOLVED se rechaza con 422 o código 1; E007 se limita a incidentes resueltos ya existentes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: exponer el registro en `POST /api/v1/incidents` y en el comando `create` de CLI, exigiendo `title` y `raw_text` no vacíos ni compuestos solo por espacios.
- **FR-002**: confirmar todo registro válido con 201 Created en web o JSON equivalente en CLI, incluyendo la clasificación completa, `is_duplicate` booleano y `duplicate_of` como lista de identificadores.
- **FR-003**: admitir como opcionales `incident_id` —autogenerado con formato `INC-HEX8` si se omite—, `created_at` —instante actual por defecto— y `status` —OPEN por defecto—; rechazar con 422 en web y código 1 en CLI un `incident_id` ya existente, sin sobrescribirlo.
- **FR-004**: rechazar `title` o `raw_text` vacíos con HTTP 422 en web y código de salida 1 en CLI, sin persistir el reporte.
- **FR-005**: clasificar el texto con el motor de triaje vigente, sin redefinir sus reglas; devolver en la respuesta la clasificación completa y persistir los campos del incidente más `recommended_team` y `duplicate_group_key`, sin exigir `rationale`, `consistency_ratio` ni `raw_text`.
- **FR-006**: considerar candidato a duplicado todo incidente distinto del recién creado cuya `duplicate_group_key` coincida exactamente y cuyo estado sea OPEN, IN_PROGRESS o ESCALATION_REQUIRED, excluyendo RESOLVED.
- **FR-007**: devolver `is_duplicate` en falso y `duplicate_of` vacío cuando no haya candidatos; el aviso nunca impide el registro ni declara causa raíz compartida.
- **FR-008**: mantener sin cambios el criterio de incidentes activos del Hito 002: solo OPEN e IN_PROGRESS para ese resumen.
- **FR-009**: exponer la auditoría de SLA en `GET /api/v1/incidents/{incident_id}/sla` y en el comando `sla` de CLI, con `reference_time` opcional en formato ISO 8601; si se omite, usar un instante actual compatible con la convención temporal del incidente almacenado.
- **FR-010**: mostrar minutos transcurridos, permitidos y restantes, incumplimiento y escalamiento, aplicando las políticas vigentes: 24/7 para P0 y P1; jornada laboral para P2 y P3; incumplimiento por exceso de minutos completos; escalamiento desde el 75% del tiempo permitido.
- **FR-011**: para incidentes resueltos, calcular hasta la fecha de resolución, conservar el incumplimiento histórico y no pedir escalamiento.
- **FR-012**: responder 404 en web y código 1 en CLI cuando el incidente no existe; responder 422 en web y código 1 en CLI cuando `reference_time` sea anterior a `created_at`, tenga formato inválido, mezcle marcas naive/aware o use offsets distintos en P2/P3.
- **FR-013**: devolver resultados equivalentes por web y terminal para el mismo registro o la misma consulta de SLA.
- **FR-014**: rechazar con 422 en web y código 1 en CLI un `status` RESOLVED en el alta; `resolved_at` solo se evalúa en incidentes ya existentes.

### Key Entities

- **Reporte entrante**: `title` y `raw_text` obligatorios; `incident_id`, `created_at` y `status` opcionales con valores por defecto.
- **Clasificación devuelta**: severidad, componente, `rationale`, `consistency_ratio`, `recommended_team` y `duplicate_group_key`, producida por el triaje vigente.
- **Incidente registrado**: identificador, título, componente, severidad, estado, fecha de creación, fecha de resolución si aplica, `recommended_team` y `duplicate_group_key`.
- **Aviso de equivalente**: bandera `is_duplicate` y lista `duplicate_of` de identificadores candidatos, sin conclusión de causa.
- **Evaluación de SLA**: incidente consultado, `reference_time`, minutos transcurridos, permitidos y restantes, incumplimiento y escalamiento.

## Success Criteria *(mandatory)*

- **SC-001**: los catorce escenarios E001–E014 pasan sus pruebas de aceptación.
- **SC-002**: el 100% de los reportes válidos queda guardado y clasificado de inmediato, con respuesta 201 Created en web y JSON equivalente en CLI.
- **SC-003**: el 100% de los casos con candidato en OPEN, IN_PROGRESS o ESCALATION_REQUIRED lista los identificadores correctos en `duplicate_of` y ningún caso RESOLVED ni el propio incidente aparece en esa lista.
- **SC-004**: el caso determinista E006 reproduce exactamente los cinco valores exigidos y las evaluaciones coinciden con la política vigente, incluidos umbral exacto e incidentes resueltos.
- **SC-005**: web y terminal devuelven resultados equivalentes ante las mismas entradas de registro y consulta.
- **SC-006**: las regresiones de los hitos anteriores continúan pasando, incluido el criterio de activos del Hito 002.

## Assumptions

- El alcance se limita al registro persistente, la detección de duplicados abiertos y la auditoría de SLA; no se implementan transiciones de estado ni cierre de incidentes.
- El aviso se entrega en la respuesta del alta; no se envían notificaciones externas.
- Se mantiene el almacenamiento ya disponible, sin nuevo motor ni datos reales; las pruebas usan almacenamiento aislado.
- No se permite registrar incidentes RESOLVED mediante el alta (Q3); los incidentes resueltos auditados provienen de datos existentes.

## Clarifications

### Session 2026-11-24

Decisiones previamente aprobadas:

- **A1 — Equivalencia**: candidato duplicado si coincide exactamente la `duplicate_group_key` y el otro incidente está en OPEN, IN_PROGRESS o ESCALATION_REQUIRED; se excluyen RESOLVED y el propio identificador recién creado. El criterio de activos del Hito 002 permanece intacto.
- **A2 — Entrada del registro**: obligatorios `title` y `raw_text` no vacíos ni solo espacios; opcionales `incident_id` con formato `INC-HEX8` autogenerado, `created_at` con el instante actual y `status` con OPEN. Se reutiliza el motor de triaje existente. La respuesta es 201 Created o JSON equivalente en CLI e incluye clasificación completa, `is_duplicate` booleano y `duplicate_of` como lista.
- **A3 — Alcance**: solo registro persistente, detección de duplicados abiertos y auditoría de SLA; sin operaciones de transición de estado ni cierre.

Requisitos obligatorios del taller verificados e incorporados:

- **T1 — Rutas y errores de registro**: `POST /api/v1/incidents` y CLI `create`; 201 Created; 422 o código 1 si `title` o `raw_text` están vacíos.
- **T2 — Duplicados**: coincidencia exacta de `duplicate_group_key` en OPEN, IN_PROGRESS y ESCALATION_REQUIRED; exclusión de RESOLVED y del propio identificador.
- **T3 — Auditoría**: `GET /api/v1/incidents/{incident_id}/sla` y CLI `sla`; `reference_time` ISO 8601 opcional.
- **T4 — Errores de consulta**: 404 si el incidente no existe; 422 si `reference_time` es anterior a `created_at`; código 1 en CLI en ambos casos.
- **T5 — Caso determinista**: P2 creado el 2026-11-06T17:00:00 y consultado el 2026-11-09T09:00:00 con `elapsed_minutes`=120, `allowed_minutes`=480, `remaining_minutes`=360, `is_breached`=false, `requires_escalation`=false.
- **T6 — Cobertura BDD**: catorce escenarios E001–E014 cubren registro, duplicados, auditoría determinista, errores y equivalencia web/CLI.

- Q: ¿Qué debe ocurrir cuando se proporciona un `incident_id` que ya está registrado? → A: Opción A: rechazar con HTTP 422 en web y código de salida 1 en CLI, sin sobrescribir el incidente existente.
- Q: ¿Qué regla debe aplicarse cuando `created_at` y `reference_time` usan convenciones de fecha distintas, una sin zona horaria y otra con zona? → A: Opción A: rechazar con 422 / código 1 la mezcla de marcas naive y aware; para P2/P3 exigir el mismo offset fijo.
- Q: ¿Debe permitirse registrar un incidente con `status` RESOLVED desde el alta? → A: Opción A: rechazar con 422 / código 1; `resolved_at` solo proviene de datos existentes.
