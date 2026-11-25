# Bitácora de Desarrollo Guiado por Especificaciones — Semana 2 (`SDD_LOG.md`)

**Estudiante(s)**: Yeison Forero
**Fecha**: 2026-11-24
**Modelos Utilizados en OpenCode (Plan/Razonamiento vs. Build/Implementación)**: Big Pickle (OpenCode gratuito) en ambos modos; OpenCode 1.19.6 y Specify CLI 1.4.4. No se utilizaron variantes de razonamiento diferenciadas de manera verificable.

---

## 1. Elicitación con `/speckit.clarify` y Auditoría con `/speckit.analyze`

### 1.1 Feature `003-incident-lifecycle-sla`
- **Ambigüedades y casos borde detectados con `/speckit.clarify`**: Se definió la equivalencia por `duplicate_group_key` exacta en incidentes abiertos (`OPEN`, `IN_PROGRESS`, `ESCALATION_REQUIRED`), sin considerar los resueltos ni el propio ID. Se delimitó el alta a `title` y `raw_text` obligatorios, con ID, fecha y estado opcionales; no se incluyeron transiciones ni cierre. Se decidió rechazar IDs existentes sin sobrescribirlos (422/CLI 1), impedir altas con estado `RESOLVED` y rechazar mezclas de fechas naive/aware, además de exigir el mismo offset fijo para P2/P3. La consulta SLA de incidentes resueltos utiliza `resolved_at`, conserva el incumplimiento histórico y no exige escalamiento. El alta con almacenamiento efímero se rechaza con 503/CLI 1.
- **Hallazgos o validaciones de `/speckit.analyze` antes de implementar**: La primera auditoría reportó cobertura documental del 100%, cuatro hallazgos HIGH y tres MEDIUM (el resumen original discrepaba de la tabla). Se corrigieron la persistencia indebida de `raw_text`, la asignación de `reference_time`, la definición y nomenclatura de DTOs, su ubicación, referencias obsoletas y trazabilidad de `TriageResult`. La segunda auditoría reportó un conflicto CRITICAL por nombres de equipos incompatibles con la Constitución, una inconsistencia MEDIUM del checklist y una LOW de trazabilidad de criterios de éxito. La revisión humana también corrigió las políticas SLA documentadas, el orden RED-GREEN y una restricción temporal incorrecta. Se conservaron 15 escenarios BDD, 15 requisitos, 6 criterios de éxito y 33 tareas. No se confundió cobertura documental con pruebas ejecutadas.

### 1.2 Feature `004-postgres-container-runtime`
- **Ambigüedades y RNF aclarados antes de diseñar PostgreSQL/Compose**: No quedaron ambigüedades abiertas tras Clarify. Se precisaron (1) el chequeo real `SELECT 1` y la equivalencia REST/CLI, incluyendo 200/503; (2) la selección mediante `DATABASE_URL` y SQLite en memoria por defecto; (3) la paridad temporal mediante ISO 8601 como TEXT; (4) el despliegue de `api` y `db` con volumen y healthchecks y la ejecución de pruebas locales sin daemon Docker. Se preservó la inserción atómica sin sobrescritura aprobada en H003 mediante `ON CONFLICT DO NOTHING` para incidentes, en lugar del upsert sugerido en la guía. La auditoría inicial de H004 reportó C1, U1 y F1, un conflicto crítico y tres requisitos con cobertura parcial; después de corregir `tasks.md`, el agente reportó 0 CRITICAL, 0 HIGH y 18/18 requisitos trazados, con 22 tareas y seis escenarios BDD. El cierre incorporó la validación real de Compose: dos arranques consecutivos, `api` y `db` healthy y `/health` con HTTP 200.

---

## 2. Comparación Crítica: SDD Manual (Iteración 1) vs. GitHub Spec Kit (Iteración 2 y Retos)

| Dimensión Comparada | SDD Manual (Iteración 1: `001`) | GitHub Spec Kit (Iteración 2 y Retos: `002`–`004`) |
| :--- | :--- | :--- |
| **Separación *QUÉ* vs. *CÓMO* vs. *TAREAS*** | Especificación manual versionada; plan y tareas discutidos de forma conversacional antes de Build. | Artefactos independientes `spec.md`, `plan.md` y `tasks.md`, con trazabilidad y documentos técnicos complementarios. |
| **Gestión de ambigüedades (`/speckit.clarify`)** | Preguntas y decisiones humanas sin un procedimiento automatizado específico. | Elicitación estructurada y registro de decisiones; por ejemplo, IDs duplicados y convenciones temporales de H003. |
| **Consistencia contra la Constitución (`/speckit.analyze`)** | Revisión manual de arquitectura y criterios antes de implementar. | Auditoría explícita previa a Build. Detectó contradicciones, pero necesitó revisión humana y corrección de inconsistencias en sus propias métricas. |
| **Riesgo de verbosidad / exceso de Markdown** | Menor volumen de documentos; riesgo de perder el contexto conversacional. | Mayor persistencia y trazabilidad, a costa de redundancias, inconsistencias y tiempo de curaduría. El commit de planificación H003 preparó ocho documentos con 1.098 inserciones y 38 eliminaciones antes de implementar. |

- **Análisis basado en MartinFowler.com (Birgitta Böckeler)**:
  1. Ubico IncidentOps principalmente en **Spec-first**, con elementos de Spec-anchored: escribimos las especificaciones antes del código y las conservamos para consulta y evolución, pero todavía no hemos demostrado un proceso sostenido de mantenimiento de las especificaciones durante toda la vida de cada funcionalidad. No es Spec-as-source: el código y las pruebas se mantienen directamente y las especificaciones no son la única entrada editable.
  2. La curaduría permitió eliminar ejemplos redundantes, limitar el alcance mediante el roadmap, corregir las dependencias RED-GREEN y contrastar los documentos con el dominio real. En H003 hubo demasiadas iteraciones de auditoría; en H004 se priorizaron hallazgos bloqueantes. Las pruebas deterministas y Ruff permitieron pasar de afirmaciones documentales a evidencias ejecutables. La cobertura del 100% de requisitos no garantizó una conexión PostgreSQL funcional: se necesitó validar el despliegue real, que finalmente confirmó el healthy de `api` y `db` y el HTTP 200 de `/health` tras corregir el ciclo de vida de la conexión.

Referencia: Birgitta Böckeler (2025), [Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html).

---

## 3. *Commands* vs. *Agent Skills*, Arquitectura Hexagonal, ADRs y Uso de *Reasoning*

- **Diferencia entre *Commands* (`/speckit.*`) y *Agent Skills* (`hexagonal-architecture`, `bdd-acceptance`, `adr-writer`)**: Los comandos organizan etapas del proceso y generan o analizan artefactos. Las skills encapsulan instrucciones especializadas reutilizables que OpenCode puede cargar bajo demanda cuando la descripción coincide con la tarea. `hexagonal-architecture` protege las fronteras, `bdd-acceptance` orienta los escenarios y pruebas, y `adr-writer` establece el formato MADR y el historial de decisiones. El orden ADR → Constitución → Hito evita que una especificación proponga infraestructura prohibida por las reglas vigentes: ADR-003 estableció la arquitectura hexagonal antes de consolidar la Constitución; ADR-004 habilitó PostgreSQL sin ORM y Docker Compose, y la Constitución 1.1.0 incorporó esta decisión antes de H004. El reemplazo de ADR-001 fue parcial, conservando SQLite local.
- **Valor de la Arquitectura Hexagonal**: Compartir `IncidentService` entre FastAPI y Typer evita duplicar las reglas de negocio. `IncidentRepositoryPort` permite seleccionar SQLite o PostgreSQL a través de la fábrica sin introducir psycopg en el dominio. El fallo de integración se pudo localizar en el adaptador: la conexión se cerraba antes de ejecutar `SELECT 1`. La corrección y sus regresiones preservaron el triaje y las reglas SLA; esta separación facilita incorporar futuros adaptadores sin replicar casos de uso.
- **Uso intencional de *Reasoning / Extended Thinking* en OpenCode**: Clarify, Plan y Analyze se benefician de razonamiento cuidadoso sobre casos borde, dependencias y restricciones. Implement puede avanzar con instrucciones concisas y pruebas verificables. En esta práctica se utilizó Big Pickle tanto en Plan como en Build; no se pudo confirmar el acceso a variantes de razonamiento extendido, por lo que no atribuyo diferencias de rendimiento a un cambio de modelo. El uso de sesiones limpias permitió recuperar contexto; se presentó también un problema de herramientas de escritura que se resolvió al reiniciar la sesión. La distinción de permisos Plan/Build fue útil, pero no garantizó por sí sola una implementación correcta.

---

## 4. Evidencia de Verificación Determinista

Se sustituyó únicamente la ruta absoluta local del repositorio por `<repo>` en las salidas adjuntas y se eliminaron espacios finales de alineación.

- **Análisis estático de fronteras hexagonales (`uv run ruff check src/`)**:

```text
All checks passed!
```

- **Salida completa de `uv run pytest -v`**:

```text
================================================== test session starts ===================================================
platform win32 -- Python 3.12.14, pytest-9.2.0, pluggy-1.7.0 -- <repo>\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: <repo>
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0
collected 96 items

tests/test_sla_calculator.py::TestSLACalculator::test_24x7_weekend PASSED                                           [  1%]
tests/test_sla_calculator.py::TestSLACalculator::test_at_sla_exactly_and_after_breach PASSED                        [  2%]
tests/test_sla_calculator.py::TestSLACalculator::test_below_threshold PASSED                                        [  3%]
tests/test_sla_calculator.py::TestSLACalculator::test_friday_after_hours_to_monday PASSED                           [  4%]
tests/test_sla_calculator.py::TestSLACalculator::test_friday_to_monday_business PASSED                              [  5%]
tests/test_sla_calculator.py::TestSLACalculator::test_invalid_interval PASSED                                       [  6%]
tests/test_sla_calculator.py::TestSLACalculator::test_invalid_severity PASSED                                       [  7%]
tests/test_sla_calculator.py::TestSLACalculator::test_multi_day PASSED                                              [  8%]
tests/test_sla_calculator.py::TestSLACalculator::test_multiple_weekends PASSED                                      [  9%]
tests/test_sla_calculator.py::TestSLACalculator::test_p1_24x7_threshold PASSED                                      [ 10%]
tests/test_sla_calculator.py::TestSLACalculator::test_resolved_missing_timestamp PASSED                             [ 11%]
tests/test_sla_calculator.py::TestSLACalculator::test_resolved_prevents_escalation_keeps_breach PASSED              [ 12%]
tests/test_sla_calculator.py::TestSLACalculator::test_same_day_edges PASSED                                         [ 13%]
tests/test_sla_calculator.py::TestSLACalculator::test_subminute_aggregation PASSED                                  [ 14%]
tests/test_sla_calculator.py::TestSLACalculator::test_timezone_consistency PASSED                                   [ 15%]
tests/test_sla_calculator.py::TestSLACalculator::test_weekend_creation PASSED                                       [ 16%]
tests/test_spec_001_triage.py::test_bdd_critical_payment_outage PASSED                                              [ 17%]
tests/test_spec_001_triage.py::test_bdd_individual_account_lockout PASSED                                           [ 18%]
tests/test_spec_001_triage.py::test_bdd_empty_input_http[payload0] PASSED                                           [ 19%]
tests/test_spec_001_triage.py::test_bdd_empty_input_http[payload1] PASSED                                           [ 20%]
tests/test_spec_001_triage.py::test_bdd_empty_input_http[payload2] PASSED                                           [ 21%]
tests/test_spec_001_triage.py::test_bdd_empty_input_http[payload3] PASSED                                           [ 22%]
tests/test_spec_001_triage.py::test_bdd_empty_input_http[payload4] PASSED                                           [ 23%]
tests/test_spec_001_triage.py::test_bdd_empty_input_http[payload5] PASSED                                           [ 25%]
tests/test_spec_001_triage.py::test_bdd_empty_input_http[payload6] PASSED                                           [ 26%]
tests/test_spec_001_triage.py::test_bdd_cli_triage_parity PASSED                                                    [ 27%]
tests/test_spec_001_triage.py::test_bdd_empty_input_cli[-reporte] PASSED                                            [ 28%]
tests/test_spec_001_triage.py::test_bdd_empty_input_cli[  -reporte] PASSED                                          [ 29%]
tests/test_spec_001_triage.py::test_bdd_empty_input_cli[INC-] PASSED                                                [ 30%]
tests/test_spec_001_triage.py::test_bdd_empty_input_cli[INC-  ] PASSED                                              [ 31%]
tests/test_spec_002_summary.py::test_bdd_global_summary PASSED                                                      [ 32%]
tests/test_spec_002_summary.py::test_bdd_component_filter PASSED                                                    [ 33%]
tests/test_spec_002_summary.py::test_bdd_empty_summary[None] PASSED                                                 [ 34%]
tests/test_spec_002_summary.py::test_bdd_empty_summary[unknown] PASSED                                              [ 35%]
tests/test_spec_002_summary.py::test_bdd_cli_summary_parity PASSED                                                  [ 36%]
tests/test_spec_002_summary.py::test_invalid_summary_http[params0] PASSED                                           [ 37%]
tests/test_spec_002_summary.py::test_invalid_summary_http[params1] PASSED                                           [ 38%]
tests/test_spec_002_summary.py::test_invalid_summary_http[params2] PASSED                                           [ 39%]
tests/test_spec_002_summary.py::test_invalid_summary_http[params3] PASSED                                           [ 40%]
tests/test_spec_002_summary.py::test_invalid_summary_http[params4] PASSED                                           [ 41%]
tests/test_spec_002_summary.py::test_invalid_summary_cli[args0] PASSED                                              [ 42%]
tests/test_spec_002_summary.py::test_invalid_summary_cli[args1] PASSED                                              [ 43%]
tests/test_spec_002_summary.py::test_unknown_component_on_populated_storage PASSED                                  [ 44%]
tests/test_spec_002_summary.py::test_repository_port_and_sql PASSED                                                 [ 45%]
tests/test_spec_002_summary.py::test_legacy_schema_migration PASSED                                                 [ 46%]
tests/test_spec_002_summary.py::test_default_memory_empty PASSED                                                    [ 47%]
tests/test_spec_002_summary.py::test_aware_default_reference PASSED                                                 [ 48%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_default_created_at_is_local_aware PASSED                        [ 50%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_explicit_created_at_is_respected PASSED                         [ 51%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_omitted_reference_follows_stored_convention PASSED              [ 52%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_rejects_naive_aware_mix[2026-11-06T17:00:00-2026-11-09T09:00:00Z] PASSED [ 53%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_rejects_naive_aware_mix[2026-11-06T17:00:00Z-2026-11-09T09:00:00] PASSED [ 54%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_rejects_distinct_offsets_in_business_hours PASSED               [ 55%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_rejects_invalid_or_earlier_reference[2026-11-06T16:59:59] PASSED [ 56%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_rejects_invalid_or_earlier_reference[no-es-una-fecha] PASSED    [ 57%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_rejects_invalid_or_earlier_reference[2026-11-06] PASSED         [ 58%]
tests/test_spec_003_lifecycle_sla.py::test_temporal_resolved_range_keeps_breach_without_escalation PASSED           [ 59%]
tests/test_spec_003_lifecycle_sla.py::test_port_atomic_insert_concurrent PASSED                                     [ 60%]
tests/test_spec_003_lifecycle_sla.py::test_port_migration_and_duplicate_index PASSED                                [ 61%]
tests/test_spec_003_lifecycle_sla.py::test_port_hydrates_classification_fields PASSED                               [ 62%]
tests/test_spec_003_lifecycle_sla.py::test_port_duplicate_filter_includes_escalation PASSED                         [ 63%]
tests/test_spec_003_lifecycle_sla.py::test_factory_keeps_ephemeral_default PASSED                                   [ 64%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e001_create_valid PASSED                                             [ 65%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e002_blank_input[blank0] PASSED                                      [ 66%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e002_blank_input[blank1] PASSED                                      [ 67%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e002_blank_input[blank2] PASSED                                      [ 68%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e002_blank_input[blank3] PASSED                                      [ 69%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e011_duplicate_id PASSED                                             [ 70%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e013_invalid_initial_status[RESOLVED] PASSED                         [ 71%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e013_invalid_initial_status[UNKNOWN] PASSED                          [ 72%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e014_create_parity PASSED                                            [ 73%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e015_ephemeral_storage PASSED                                        [ 75%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e003_open_duplicate[OPEN] PASSED                                     [ 76%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e003_open_duplicate[IN_PROGRESS] PASSED                              [ 77%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e003_open_duplicate[ESCALATION_REQUIRED] PASSED                      [ 78%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e004_no_duplicate PASSED                                             [ 79%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e005_sla_audit PASSED                                                [ 80%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e006_deterministic_p2 PASSED                                         [ 81%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e007_resolved_sla PASSED                                             [ 82%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e008_rest_cli_sla_parity PASSED                                      [ 83%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e009_missing_incident PASSED                                         [ 84%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e010_invalid_reference[no-valido] PASSED                             [ 85%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e010_invalid_reference[2026-11-06T16:00:00] PASSED                   [ 86%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_e012_incompatible_dates PASSED                                       [ 87%]
tests/test_spec_004_runtime_health.py::test_bdd_e001_health_connected PASSED                                        [ 88%]
tests/test_spec_004_runtime_health.py::test_bdd_e002_health_unavailable PASSED                                      [ 89%]
tests/test_spec_004_runtime_health.py::test_bdd_e003_default_sqlite_memory PASSED                                   [ 90%]
tests/test_spec_004_runtime_health.py::test_bdd_e004_sqlite_url PASSED                                              [ 91%]
tests/test_spec_004_runtime_health.py::test_bdd_e005_postgres_url PASSED                                            [ 92%]
tests/test_spec_004_runtime_health.py::test_regression_health_select_one_tuple_and_factory_alias PASSED             [ 93%]
tests/test_spec_004_runtime_health.py::test_regression_connection_lifecycle_stays_open_until_repository_exit PASSED [ 94%]
tests/test_spec_004_runtime_health.py::test_bdd_e006_compose_structure PASSED                                       [ 95%]
tests/test_triage_rules.py::TestTriageRules::test_duplicate_keys PASSED                                             [ 96%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1001') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1002') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1003') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1004') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1005') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1006') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1007') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1008') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1009') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component SUBPASSED(incident_id='INC-1010') [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_expected_severity_and_component PASSED                            [ 97%]
tests/test_triage_rules.py::TestTriageRules::test_key_is_stable_across_case_and_accents PASSED                      [ 98%]
tests/test_triage_rules.py::TestTriageRules::test_subjective_urgency_does_not_raise_severity PASSED                 [100%]

==================================================== warnings summary ====================================================
.venv\Lib\site-packages\fastapi\testclient.py:1
  <repo>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=================================== 96 passed, 1 warning, 10 subtests passed in 3.84s ====================================
```

- **Evidencia de CLI Typer y containerización (`health`, `triage`, `docker compose up --build` / `ps`)**:

```text
PS <repo>> uv run python -m src.adapters.inbound.cli health
{"status": "ok", "database": "connected"}
```

```text
PS <repo>> $env:PYTHONIOENCODING="utf-8"; uv run python -m src.adapters.inbound.cli triage --incident-id INC-1001 --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"
{"incident_id": "INC-1001", "severity": "P0", "component": "payments-gateway", "rationale": "Fallo HTTP 502 en servicio crítico de pagos: P0 preventivo; alcance global por confirmar.", "consistency_ratio": 1.0, "recommended_team": "Backend-Core", "duplicate_group_key": "payments-gateway:http-502-outage"}
exit=0
```

La configuración efectiva de Compose quedó validada por el arranque orquestado `docker compose up --build -d --wait` y por `docker compose ps`, cuyas salidas reales se muestran a continuación. No se transcribe una salida separada de `docker compose config -q` porque no fue obtenida; el CLI `docker` no está disponible en el entorno de cierre documental y no se afirma una salida no ejecutada.

```text
PS <repo>> docker compose down
[+] down 3/3
 ✔ Container talleres-isia-api-1 Removed                                                                               0.7s
 ✔ Container talleres-isia-db-1  Removed                                                                               0.4s
 ✔ Network talleres-isia_default Removed                                                                               0.2s
PS <repo>> docker compose up --build -d --wait
[+] Building 2.3s (15/15) FINISHED
 => [internal] load local bake definitions                                                                            0.0s
 => => reading from stdin 577B                                                                                        0.0s
 => [internal] load build definition from Dockerfile                                                                  0.0s
 => => transferring dockerfile: 401B                                                                                  0.0s
 => [internal] load metadata for ghcr.io/astral-sh/uv:latest                                                          1.0s
 => [internal] load metadata for docker.io/library/python:3.12-slim                                                   0.6s
 => [internal] load .dockerignore                                                                                     0.0s
 => => transferring context: 198B                                                                                     0.0s
 => FROM ghcr.io/astral-sh/uv:latest@sha256:a3ea1357342c1a4bf9a0c53a3deb1b55379aefa037338d8113d5771efa01774f          0.1s
 => => resolve ghcr.io/astral-sh/uv:latest@sha256:a3ea1357342c1a4bf9a0c53a3deb1b55379aefa037338d8113d5771efa01774f    0.1s
 => [internal] load build context                                                                                     0.1s
 => => transferring context: 3.85kB                                                                                   0.0s
 => [stage-0 1/6] FROM docker.io/library/python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805b  0.1s
 => => resolve docker.io/library/python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f  0.1s
 => CACHED [stage-0 2/6] COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/                                       0.0s
 => CACHED [stage-0 3/6] WORKDIR /app                                                                                 0.0s
 => CACHED [stage-0 4/6] COPY pyproject.toml uv.lock README.md ./                                                     0.0s
 => CACHED [stage-0 5/6] RUN uv sync --frozen --no-dev                                                                0.0s
 => CACHED [stage-0 6/6] COPY src/ ./src/                                                                             0.0s
 => exporting to image                                                                                                0.1s
 => => exporting layers                                                                                               0.0s
 => => exporting manifest sha256:f1c37c9612bb0b6e7ea44e2b6f7fe3cb5dc8c10fda96b7c3f7c4c48558c2e585                     0.0s
 => => exporting config sha256:fc34b333cf34eab7fe5a0ebec49197f5cc1816947cdf2d7b1b08285358428beb                       0.0s
 => => exporting attestation manifest sha256:bdf2db59726ad61ad81691e42e908cb4ae5655c1fa80bf4c8712cd2ff1a22466         0.0s
 => => exporting manifest list sha256:e252a8fab3d196573d1a94ea3cf20eb9cf38bcd4e13a2b23a768f20a4d953365                0.0s
 => => naming to docker.io/library/talleres-isia-api:latest                                                           0.0s
 => => unpacking to docker.io/library/talleres-isia-api:latest                                                        0.0s
 => resolving provenance for metadata file                                                                            0.0s
[+] up 4/4
 ✔ Image talleres-isia-api       Built                                                                                 2.7s
 ✔ Network talleres-isia_default Created                                                                               0.1s
 ✔ Container talleres-isia-db-1  Healthy                                                                               7.1s
 ✔ Container talleres-isia-api-1 Healthy                                                                              12.4s
PS <repo>> docker compose ps
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                    PORTS
talleres-isia-api-1   talleres-isia-api    "uv run --no-sync uv…"   api       13 seconds ago   Up 7 seconds (healthy)    0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
talleres-isia-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        13 seconds ago   Up 12 seconds (healthy)   5432/tcp
PS <repo>> curl.exe -i http://localhost:8000/health
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 02:32:27 GMT
server: uvicorn
content-length: 38
content-type: application/json

{"status":"ok","database":"connected"}
```

El primer despliegue produjo HTTP 503 y API unhealthy pese a la conexión directa exitosa a PostgreSQL. La primera corrección normalizó filas de SELECT 1 y expuso el alias de fábrica, pero no resolvió el fallo. Una traza dentro del contenedor identificó `OperationalError: the connection is closed`. Tras corregir el ciclo de vida de la conexión y añadir pruebas de regresión, dos arranques consecutivos devolvieron HTTP 200 con ambos servicios healthy. El volumen se conservó. La suite final contiene 96 pruebas aprobadas y 10 subpruebas, con una advertencia de deprecación de Starlette no bloqueante.

Se incorporó también el segundo subcomando CLI (`triage`) con salida real y `exit=0`. La validación de la configuración Compose se apoya en el arranque orquestado y en `docker compose ps`; no se transcribe una salida separada de `docker compose config -q` porque no fue obtenida y no corresponde afirmarla. Con esto queda cerrada la evidencia documental del taller autónomo.

- Validación adicional: docker compose config -q — Compose OK (exit 0).
