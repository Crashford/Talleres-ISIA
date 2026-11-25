# Feature Specification: H003 — Ciclo de vida, duplicados y SLA

**Feature Branch**: `practica-guiada-sdd-semana-2` | **Created**: 2026-11-24 | **Status**: curado tras revisión humana de `/speckit.plan` y `/speckit.analyze`; pendiente de autorización para Build

**Input**: Operaciones necesita guardar los incidentes cuando llegan, avisar si ya existe otro equivalente abierto y consultar cómo va su SLA desde la web y desde la terminal.

**Contrato observable frente a detalle interno**: los escenarios E001–E015, los requisitos FR-001–FR-015 y los criterios SC-001–SC-006 describen solo comportamiento observable por REST y CLI: rutas, comandos, códigos HTTP y de salida, y campos JSON. Los DTOs, las dataclasses, Pydantic, las rutas de código y las decisiones de persistencia se documentan en `plan.md`, `research.md`, `data-model.md` y `contracts/incidents.md`.

## User Scenarios & Testing *(mandatory)*

### US1 — Registrar el incidente entrante (P1)

Operaciones necesita que cada reporte que llega quede guardado y clasificado de inmediato.

**Independent Test**: registrar un reporte con título y texto válidos en almacenamiento persistente, mediante la web y la terminal, y comprobar la respuesta y la consulta posterior.

- **E001 — Given** un título y un texto sin clasificar, ambos no vacíos, y almacenamiento persistente, **When** se envía `POST /api/v1/incidents` o el comando `create` de CLI, **Then** se guarda con identificador autogenerado `INC-HEX8`, fecha de creación actual con offset local y estado OPEN; la web responde 201 Created y la CLI devuelve JSON equivalente, con la clasificación completa, `is_duplicate` en falso y `duplicate_of` vacío cuando no hay candidatos.
- **E002 — Given** un título o texto vacío o formado solo por espacios, **When** se intenta registrar, **Then** la web responde 422 y la CLI termina con código de salida 1, sin guardar ningún incidente.
- **E011 — Given** un incidente ya registrado con un identificador concreto, **When** se intenta registrar otro reporte con ese mismo `incident_id`, incluso mediante altas concurrentes, **Then** la web responde 422 y la CLI termina con código 1, y el incidente existente permanece sin cambios.
- **E013 — Given** un intento de registro con `status` RESOLVED o desconocido, **When** se envía `POST /api/v1/incidents` o el comando `create` de CLI, **Then** la web responde 422 y la CLI termina con código 1, sin guardar el incidente.
- **E014 — Given** los mismos datos de entrada, `incident_id` y `created_at` explícitos en almacenamientos aislados equivalentes, **When** se registra mediante `POST /api/v1/incidents` y mediante CLI `create`, **Then** ambas respuestas contienen el mismo identificador, fecha de creación, clasificación, `is_duplicate` y `duplicate_of`.
- **E015 — Given** una configuración de almacenamiento efímero que no conserva datos entre operaciones, **When** se intenta registrar un incidente, **Then** la web responde 503 y la CLI termina con código 1, sin guardar ni devolver un éxito falso.

### US2 — Avisar de equivalentes abiertos (P1)

Operaciones necesita detectar posibles duplicados en el momento del alta, sin perder el reporte entrante.

**Independent Test**: registrar un reporte cuya `duplicate_group_key` coincide con la de un incidente en estado abierto y comprobar el aviso; repetir sin esa coincidencia.

- **E003 — Given** otro incidente en OPEN, IN_PROGRESS o ESCALATION_REQUIRED con la misma `duplicate_group_key` exacta, **When** se registra el nuevo reporte, **Then** se guarda igualmente y la respuesta marca `is_duplicate` en verdadero y lista en `duplicate_of` los identificadores de esos incidentes, excluido el propio, sin afirmar causa raíz compartida.
- **E004 — Given** que el único incidente con esa clave está RESOLVED o que ningún incidente coincide con la clave calculada, **When** se registra, **Then** el incidente se guarda con `is_duplicate` en falso y `duplicate_of` vacío.

### US3 — Auditar el SLA desde ambas interfaces (P2)

Operaciones y Soporte necesitan saber en cualquier instante cómo va el SLA de un incidente, con el mismo resultado en web y terminal.

**Independent Test**: fijar un instante de referencia explícito, consultar el mismo incidente en ambas interfaces sobre el mismo almacenamiento compartido y comparar el resultado.

- **E005 — Given** un incidente guardado con fecha de creación conocida, **When** se consulta `GET /api/v1/incidents/{incident_id}/sla` o el comando `sla` de CLI con un `reference_time` ISO 8601 opcional, **Then** se muestran `reference_time` efectivo, minutos transcurridos, permitidos y restantes, si incumplió y si requiere escalamiento, según la política de SLA vigente.
- **E006 — Given** un incidente P2 creado el viernes 2026-11-06T17:00:00 y consultado con `reference_time` 2026-11-09T09:00:00, **When** se audita su SLA, **Then** `elapsed_minutes`=120, `allowed_minutes`=480, `remaining_minutes`=360, `is_breached`=false y `requires_escalation`=false.
- **E007 — Given** un incidente resuelto procedente de datos existentes y un `reference_time` válido, **When** se consulta su SLA, **Then** se valida la referencia respecto de `created_at` y las convenciones temporales, el cálculo usa `resolved_at`, conserva el incumplimiento histórico y no pide escalamiento; no se reconstruye el estado histórico.
- **E008 — Given** el mismo incidente guardado en un almacenamiento compartido y el mismo `reference_time` explícito, **When** se consulta por web y por terminal, **Then** ambas interfaces devuelven el mismo resultado, incluido `reference_time`.
- **E009 — Given** un identificador de incidente que no existe, **When** se consulta su SLA por web o por terminal, **Then** la web responde 404 y la CLI termina con código 1, con una explicación clara.
- **E010 — Given** un `reference_time` con formato inválido o anterior a `created_at`, **When** se consulta el SLA, **Then** la web responde 422 y la CLI termina con código 1, sin devolver un cálculo engañoso.
- **E012 — Given** un incidente con `created_at` aware y `reference_time` naive, o con `created_at` naive y `reference_time` aware, o dos marcas aware con offsets distintos en P2/P3, **When** se consulta el SLA, **Then** la web responde 422 y la CLI termina con código 1, sin devolver un cálculo; si `reference_time` se omite, se usa un instante actual compatible con la convención temporal del incidente almacenado.

### Edge Cases

- Si se omite `incident_id`, se autogenera con formato `INC-HEX8`; si se proporciona, debe ser texto no vacío y `INC-HEX8` no se exige para IDs entrantes. Un ID existente se rechaza sin sobrescribir, incluso en altas concurrentes.
- `created_at` omitido usa el instante actual local con offset del entorno; la zona depende del entorno, por lo que la paridad determinista requiere fechas explícitas. Las fechas proporcionadas se respetan y ADR-002 se mantiene.
- Para el aviso se excluyen los incidentes RESOLVED y el identificador recién creado; el criterio de incidentes activos del Hito 002 (OPEN e IN_PROGRESS) no se modifica.
- El incumplimiento se produce solo cuando los minutos completos exceden el límite; el escalamiento empieza en el 75% exacto y se mantiene tras el vencimiento mientras no se resuelva.
- No hay festivos configurados. Se rechazan con 422 o código 1 las mezclas naive/aware en cualquier orden y, para P2/P3, los offsets distintos entre `created_at` y `reference_time`; la validación aplica también a incidentes resueltos.
- Se rechazan con 422 o código 1 `status` RESOLVED y estados desconocidos; E007 se limita a incidentes resueltos ya existentes y no implica transiciones de estado.
- El alta requiere almacenamiento que conserve datos entre operaciones; con almacenamiento efímero por operación se responde 503 o código 1 sin falso éxito.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: exponer el registro en `POST /api/v1/incidents` y en el comando `create` de CLI, exigiendo `title` y `raw_text` no vacíos ni compuestos solo por espacios.
- **FR-002**: confirmar todo registro válido con 201 Created en web o JSON equivalente en CLI, incluyendo la clasificación completa, `is_duplicate` booleano y `duplicate_of` como lista de identificadores, sin `raw_text` en la respuesta.
- **FR-003**: admitir como opcionales `incident_id` —autogenerado con formato `INC-HEX8` si se omite, texto no vacío si se proporciona—, `created_at` —instante actual local con offset si se omite— y `status` —OPEN por defecto—; admitir OPEN, IN_PROGRESS y ESCALATION_REQUIRED como estados iniciales; rechazar con 422/código 1 un ID repetido sin sobrescribir ni persistir, y rechazar RESOLVED y estados desconocidos. No se usa HTTP 409.
- **FR-004**: rechazar `title` o `raw_text` vacíos con HTTP 422 en web y código de salida 1 en CLI, sin persistir el reporte.
- **FR-005**: clasificar el texto recibido con el motor de triaje vigente, sin redefinir sus reglas; devolver la clasificación completa y persistir solo los campos del incidente más `recommended_team` y `duplicate_group_key`. `raw_text` se usa únicamente como entrada del triaje: no se persiste ni se devuelve.
- **FR-006**: considerar candidato a duplicado todo incidente distinto del recién creado cuya `duplicate_group_key` coincida exactamente y cuyo estado sea OPEN, IN_PROGRESS o ESCALATION_REQUIRED, excluyendo RESOLVED.
- **FR-007**: devolver `is_duplicate` en falso y `duplicate_of` vacío cuando no haya candidatos; con candidato, el incidente se guarda igualmente con 201 y `is_duplicate` en verdadero. El aviso nunca impide el registro ni declara causa raíz compartida, y no se usa HTTP 409.
- **FR-008**: mantener sin cambios el criterio de incidentes activos del Hito 002: solo OPEN e IN_PROGRESS para ese resumen.
- **FR-009**: exponer la auditoría de SLA en `GET /api/v1/incidents/{incident_id}/sla` y en el comando `sla` de CLI, con `reference_time` opcional en formato ISO 8601; si se omite, usar un instante actual compatible con la convención temporal del incidente almacenado; devolver siempre el `reference_time` efectivo.
- **FR-010**: mostrar minutos transcurridos, permitidos y restantes, incumplimiento y escalamiento, aplicando las políticas vigentes: 24/7 para P0 y P1; jornada laboral para P2 y P3; incumplimiento por exceso de minutos completos; escalamiento desde el 75% del tiempo permitido.
- **FR-011**: para incidentes resueltos, calcular hasta `resolved_at`, conservar el incumplimiento histórico y no pedir escalamiento; validar `reference_time` también en este caso y no reconstruir el estado histórico.
- **FR-012**: responder 404 en web y código 1 en CLI cuando el incidente no existe; responder 422 en web y código 1 en CLI cuando `reference_time` sea anterior a `created_at`, tenga formato inválido, mezcle marcas naive/aware o use offsets distintos en P2/P3, incluso para resueltos.
- **FR-013**: devolver resultados equivalentes por web y terminal: el alta con almacenamientos aislados equivalentes y `incident_id`/`created_at` explícitos, y las consultas con el mismo almacenamiento compartido y `reference_time` explícito.
- **FR-014**: rechazar con 422 en web y código 1 en CLI un `status` RESOLVED o desconocido en el alta; `resolved_at` solo se evalúa en incidentes ya existentes.
- **FR-015**: rechazar el alta con HTTP 503 en web y código 1 en CLI cuando el almacenamiento configurado sea efímero por operación, sin falso éxito; la configuración de almacenamiento permanece fuera del dominio y de las reglas de negocio.

### Key Entities

- **Reporte entrante**: `title` y `raw_text` obligatorios; `incident_id`, `created_at` y `status` opcionales con valores por defecto y validación acordada. `raw_text` alimenta el triaje y no forma parte del incidente persistido ni de la respuesta.
- **Clasificación devuelta**: severidad, componente, `rationale`, `consistency_ratio`, `recommended_team` y `duplicate_group_key`, producida por el triaje vigente y propagada sin duplicar sus reglas.
- **Incidente registrado**: identificador, título, componente, severidad, estado, fecha de creación, fecha de resolución si aplica, `recommended_team` y `duplicate_group_key`.
- **Aviso de equivalente**: bandera `is_duplicate` y lista `duplicate_of` de identificadores candidatos, sin conclusión de causa.
- **Evaluación de SLA**: incidente consultado, `reference_time` efectivo, minutos transcurridos, permitidos y restantes, incumplimiento y escalamiento.

## Success Criteria *(mandatory)*

- **SC-001**: los quince escenarios E001–E015 pasan sus pruebas de aceptación, incluida la concurrencia sobre el mismo identificador y el rechazo de almacenamiento efímero.
- **SC-002**: el 100% de los reportes válidos con almacenamiento persistente queda guardado y clasificado de inmediato, con respuesta 201 Created en web y JSON equivalente en CLI.
- **SC-003**: el 100% de los casos con candidato en OPEN, IN_PROGRESS o ESCALATION_REQUIRED lista los identificadores correctos en `duplicate_of` y ningún caso RESOLVED ni el propio incidente aparece en esa lista.
- **SC-004**: el caso determinista E006 reproduce exactamente los cinco valores exigidos y las evaluaciones coinciden con la política vigente, incluidos umbral exacto e incidentes resueltos.
- **SC-005**: web y terminal devuelven resultados equivalentes ante las mismas entradas de registro y consulta, con el aislamiento o compartición de almacenamiento acordado para cada caso.
- **SC-006**: las regresiones de los hitos anteriores continúan pasando, incluido el criterio de activos del Hito 002; se identifican sin eliminar ni debilitar las pruebas que puedan requerir ajustes mínimos de fixtures.

## Assumptions

- El alcance se limita al registro persistente, la detección de duplicados abiertos y la auditoría de SLA; no se implementan transiciones de estado ni cierre de incidentes, ni se reconstruye el estado histórico de resueltos.
- El aviso se entrega en la respuesta del alta; no se envían notificaciones externas.
- Se mantiene el almacenamiento ya disponible, sin nuevo motor ni datos reales; las pruebas usan almacenamiento aislado. `sqlite:///:memory:` se conserva para desarrollo y operaciones compatibles, pero no basta para el alta persistente.
- No se permite registrar incidentes RESOLVED mediante el alta (Q3); los incidentes resueltos auditados provienen de datos existentes.
- Las operaciones persistentes de H003 usan `DATABASE_URL` con archivo SQLite; la zona local depende del entorno y la paridad determinista requiere fechas explícitas.

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
- **T6 — Cobertura BDD**: quince escenarios E001–E015 cubren registro, concurrencia, duplicados, auditoría determinista, errores, almacenamiento y equivalencia web/CLI.

- Q: ¿Qué debe ocurrir cuando se proporciona un `incident_id` que ya está registrado? → A: Opción A: rechazar con HTTP 422 en web y código de salida 1 en CLI, sin sobrescribir el incidente existente.
- Q: ¿Qué regla debe aplicarse cuando `created_at` y `reference_time` usan convenciones de fecha distintas, una sin zona horaria y otra con zona? → A: Opción A: rechazar con 422 / código 1 la mezcla de marcas naive y aware; para P2/P3 exigir el mismo offset fijo.
- Q: ¿Debe permitirse registrar un incidente con `status` RESOLVED desde el alta? → A: Opción A: rechazar con 422 / código 1; `resolved_at` solo proviene de datos existentes.

### Curaduría posterior a `/speckit.plan` (2026-11-24)

- **D01**: el ID existente se rechaza sin sobrescritura, incluso en altas concurrentes, con 422/código 1; la inserción atómica, el puerto y la traducción del error se documentan en `data-model.md` y `plan.md`.
- **D02**: `created_at` omitido toma el instante actual con offset local; se respetan fechas explícitas y ADR-002; la zona depende del entorno y la paridad determinista requiere fechas explícitas. La normalización interna se documenta en `data-model.md` y `plan.md`.
- **D03**: estados iniciales válidos OPEN, IN_PROGRESS y ESCALATION_REQUIRED; se rechazan RESOLVED y desconocidos; ID proporcionado debe ser texto no vacío y `INC-HEX8` aplica solo a generación automática.
- **D04**: SLA de resueltos se calcula hasta `resolved_at`, con validación temporal de `reference_time`, sin reconstruir estado histórico; la respuesta incluye `reference_time` y la paridad se comprueba con referencias explícitas.
- **D05**: `sqlite:///:memory:` se conserva como predeterminado; el alta persistente exige almacenamiento entre operaciones, y un almacenamiento efímero se rechaza con 503/código 1 sin falso éxito; la configuración queda fuera del dominio.
- **H06**: ejemplos P0 y P2 usan identificadores diferentes; el caso P2 reproduce los cinco resultados exigidos.
- **H07**: se identifican regresiones H002 que pueden requerir ajustes mínimos de fixtures por la extensión de `Incident`, sin eliminar pruebas ni debilitar aserciones.
- **H08**: paridad de creación usa almacenamientos aislados equivalentes; paridad de consultas REST/CLI usa el mismo archivo SQLite.

### Curaduría posterior a `/speckit.analyze` (2026-11-24)

- **Analyze-A1**: `raw_text` queda exclusivamente como entrada del registro para el motor de triaje; no es atributo de `Incident`, no se persiste y no aparece en la respuesta REST/CLI.
- **Analyze-A2**: el `reference_time` efectivo es observable en la respuesta REST/CLI; la decisión de no extender el cálculo y la ubicación interna de ese campo se documentan en `data-model.md` y `plan.md`.
- **Analyze-A3/A4/A5**: la correspondencia entre DTOs de aplicación, dataclasses, Pydantic y esquemas HTTP se documenta en `data-model.md`, `plan.md` y `research.md`; el contrato observable son los campos JSON de REST y CLI.
- **Analyze-A6**: `tasks.md` existe y está curado; la documentación no afirma que la implementación o las pruebas ya se ejecutaron.
- **Analyze-A7**: la trazabilidad de `severity`, `component`, `rationale`, `consistency_ratio`, `recommended_team` y `duplicate_group_key` de `TriageResult` queda explícita sin redefinir el triaje vigente.
- **Revisión HTTP 409**: no aprobado. Un equivalente abierto se registra con 201, `is_duplicate: true` y `duplicate_of` con los candidatos; un `incident_id` existente se rechaza con 422/código CLI 1 sin sobrescribir. HTTP 503 y código CLI 1 se mantienen para almacenamiento efímero por operación.
- **Duplicación y severidades**: se eliminan las notas redundantes sobre `tasks.md`; la duplicación contabilizada por Analyze correspondía a esas notas. La tabla de hallazgos tiene 4 HIGH y 3 MEDIUM; el recuento de métricas inicial era erróneo y queda corregido en el informe final.
