# Research — H003: ciclo de vida, duplicados y SLA

**Spec**: [spec.md](spec.md) | **Rama Git activa**: `practica-guiada-sdd-semana-2` | **Fecha**: 2026-11-24

**Estado**: decisiones D01–D05, correcciones H06–H08 y curaduría Analyze-A1–A7 aprobadas por revisión humana; sin implementación ni ejecución de pruebas.

## Reutilización verificada de H001/H002

- Triaje único: `classify_incident_report` en `src/domain/triage_rules.py:95`; clave de correlación en `:107`.
- SLA único: `SLA_POLICY_TABLE` en `src/domain/sla_calculator.py:12` y `evaluate_sla_status` en `:46`.
- Puerto existente: `IncidentRepositoryPort` en `src/application/ports.py:9`; composición en `src/adapters/outbound/factory.py:11`.
- Adaptador SQLite: esquema/migración en `src/adapters/outbound/sqlite_repository.py:32-71`; filtro activo H002 en `:115` debe permanecer.
- Interfaces: `create_app` en `src/adapters/inbound/api/app.py:14` y comandos en `src/adapters/inbound/cli.py:19,32`; ambos delegan en `IncidentService`.
- Fronteras Ruff vigentes: `pyproject.toml:29-30` y los `ruff.toml` jerárquicos de dominio, aplicación e inbound.
- Línea base documental: 51 pruebas y 10 subpruebas en `evidence/H002-verificacion.md:15,18`; no se reejecutaron en esta curaduría.

## Decisiones aprobadas

| Ref. | Decisión | Justificación y alternativas descartadas |
|---|---|---|
| D01 | `save_incident` usa `INSERT ... ON CONFLICT(incident_id) DO NOTHING`, devuelve booleano y el servicio traduce `False` a `ValidationError`. Se añade cobertura de altas concurrentes con el mismo ID y se preserva el registro original. | La PRIMARY KEY evita TOCTOU incluso entre procesos; se descarta comprobar antes de guardar y añadir un segundo método de inserción. |
| D02 | La normalización temporal se centraliza en `sla_calculator.py`. Si `created_at` se omite, se usa `datetime.now().astimezone()`; las fechas explícitas se respetan y ADR-002 se mantiene. | La zona local depende del entorno: la paridad determinista exige fechas explícitas. Se descarta UTC fijo y parseo en adaptadores. |
| D03 | Estados iniciales válidos: OPEN, IN_PROGRESS y ESCALATION_REQUIRED. Se rechazan RESOLVED y desconocidos. El `incident_id` proporcionado debe ser texto no vacío; `INC-HEX8` aplica solo a la generación automática. | Derivado de E013/FR-014; se descarta validar un formato no exigido por la spec para IDs entrantes. |
| D04 | El SLA de resueltos se calcula hasta `resolved_at`, conserva incumplimiento histórico y no escala. `reference_time` se valida respecto de `created_at` y convenciones temporales también para resueltos; se incluye en la respuesta y la paridad se comprueba con referencias explícitas. No se reconstruye el estado histórico. | Resuelve la ambigüedad entre E007 y FR-012 sin introducir transiciones; se descarta una línea temporal de estados. |
| D05 | Se conserva `sqlite:///:memory:` por defecto. El adaptador expone una capacidad neutral de persistencia; si la configuración es efímera por operación, `create_incident` falla con HTTP 503/código CLI 1 sin falso éxito. Las operaciones persistentes usan `DATABASE_URL` con archivo SQLite. | La configuración permanece en el adaptador y fuera del dominio/reglas de negocio; se descartan cambiar el default, memoria compartida, PostgreSQL, Docker y nuevas dependencias. |
| H06 | Los ejemplos P0 y P2 usan identificadores distintos; el caso P2 reproduce 120/480/360, `false`, `false`. | Evita mezclar un alta P0 con una auditoría P2 en el mismo ID. |
| H07 | Se revisan regresiones H002 susceptibles de ajustes mínimos de fixtures por la extensión de `Incident`; no se eliminan pruebas ni se debilitan aserciones. | Los campos nuevos se añaden al final con valores por defecto; la verificación real se reserva para Build. |
| H08 | Paridad de creación con almacenamientos aislados equivalentes; paridad de consultas REST/CLI con el mismo archivo SQLite. | Refleja la semántica de E014/E008 y evita comparar resultados sobre bases vacías distintas. |
| Arquitectura | `TeamName` deriva del `Literal` existente; `Incident` se amplía al final del dataclass; `create_incident`, `evaluate_incident_sla` y `IncidentNotFoundError` viven en aplicación; la migración es aditiva con `idx_incidents_dup_key`. | Conserva principios I–V y ADR-001/002/003; se descartan duplicar reglas, reconstruir tablas y ampliar el resumen H002. |
| Rama | `setup-plan.sh` informa un slug derivado de `feature.json`; la rama Git verificada es `practica-guiada-sdd-semana-2` y no se cambia. | `common.sh:217-224`; se descarta renombrar la rama. |

## Decisiones posteriores a `/speckit.analyze`

| Ref. | Decisión | Justificación y alcance |
|---|---|---|
| Analyze-A1 | `raw_text` es entrada del caso de uso y del triaje, no atributo de `Incident`, campo persistido ni dato de respuesta. | Evita duplicar el texto entrante en el modelo y en el contrato; el triaje vigente sigue siendo el único consumidor. |
| Analyze-A2 | `SLAEvaluation` conserva sus campos actuales. `reference_time` se expone en `IncidentSLAResult` y `SLAEvaluationResponse`. | Separa dominio de representación sin cambiar ADR-002 ni el cálculo. |
| Analyze-A3/A4 | DTOs de aplicación: `IncidentCreatedResult` e `IncidentSLAResult`. Esquemas HTTP: `CreateIncidentRequest`, `IncidentCreatedResponse`, `SLAEvaluationResponse`. | Unifica nomenclatura en spec, plan, modelo, contrato y tareas. |
| Analyze-A5 | `src/application/dtos.py` es la ubicación aprobada para los DTOs de aplicación como dataclasses. | Respeta la frontera hexagonal: aplicación no importa Pydantic ni adaptadores; los adaptadores solo mapean. |
| Analyze-A6 | `tasks.md` existe y está curado; no se afirma implementación ni pruebas ejecutadas. | Elimina la duplicación documental detectada por Analyze. |
| Analyze-A7 | `TriageResult` se reutiliza; sus seis campos quedan trazados hasta el DTO y la respuesta. | Completa cobertura sin redefinir `classify_incident_report`. |
| HTTP 409/503 | No se usa 409. Equivalente abierto: 201 con aviso; ID existente: 422/código 1 sin sobrescritura; almacenamiento efímero: 503/código 1 sin falso éxito. | Conserva el contrato aprobado y evita introducir un código de respuesta no autorizado. |
| Métricas Analyze | La tabla contiene 4 hallazgos HIGH y 3 MEDIUM; la duplicación contabilizada correspondía a las notas obsoletas de `tasks.md`. | Corrige el recuento final informado sin alterar las decisiones. |

## Ajuste mínimo del puerto

- `save_incident(...) -> bool`: inserción atómica; `True` si insertó, `False` si el ID ya existía.
- `supports_persistent_writes() -> bool`: capacidad expuesta por el adaptador según la configuración; la aplicación solo decide fallar el alta, sin conocer SQLite ni `DATABASE_URL`.
- `get_incident` hidrata `recommended_team` y `duplicate_group_key`; `find_open_duplicates` incluye ESCALATION_REQUIRED; `list_active_incidents` permanece con OPEN e IN_PROGRESS.

## Impacto en regresiones H002 (H07)

| Prueba | Impacto previsto | Acción permitida |
|---|---|---|
| `tests/test_spec_002_summary.py:21-25` (`make_incident`) | Constructor posicional sigue válido porque los campos nuevos se añaden al final con `None`. | Ninguna, salvo fallo real verificado. |
| `tests/test_spec_002_summary.py:114-130` (`test_repository_port_and_sql`) | Puede requerir ajuste mínimo de fixture para reflejar la hidratación de campos nuevos y la capacidad de persistencia; `get_incident == a` y el contrato del puerto deben conservarse. | Ajustar solo la preparación, nunca eliminar aserciones ni debilitar el contrato. |
| `tests/test_spec_002_summary.py:134-142` (`test_legacy_schema_migration`) | La migración debe añadir `recommended_team` sin perder la fila legacy ni `duplicate_group_key`. | Verificar; no reescribir la prueba salvo evidencia de fallo. |
| `tests/test_spec_002_summary.py:145-149` (`test_default_memory_empty`) | El resumen en memoria sigue vacío y exitoso; el rechazo 503 aplica solo al alta. | Sin cambios. |
| `tests/test_spec_002_summary.py:152-159` (`test_aware_default_reference`) | La centralización temporal debe preservar el comportamiento aware. | Sin cambios. |

## Riesgos y contradicciones resueltas

- D01 cambia la semántica histórica de upsert; queda aprobada, pero exige evidencia de concurrencia y de regresiones H002 antes de cerrar el hito.
- D02 hace que el offset por defecto dependa del entorno; por eso E008/E014 y el contrato usan fechas y referencias explícitas.
- D05 mantiene la base efímera por diseño; el falso éxito se evita en el alta mediante la capacidad del puerto, sin mover configuración al dominio.
- ADR-002 no contempla festivos, zonas múltiples ni DST dentro del tramo; el contrato no debe sugerirlos. D04 elimina la ambigüedad sobre resueltos.
- ADR-001 acepta el costo del nuevo índice; cualquier cambio de motor requiere un ADR nuevo y queda fuera de H003.
- ADR-002 nombra rutas heredadas (`src/sla_calculator.py`); se conserva la decisión, no se reescribe el ADR.
- No quedan decisiones técnicas pendientes de aprobación; sí queda pendiente la verificación real mediante Ruff y pytest durante Build.
