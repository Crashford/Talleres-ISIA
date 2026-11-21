# Bitácora de Ingeniería de Prompts y Contexto — Semana 1 (`CONTEXT_LOG.md`)

**Estudiante(s)**: `Yeison Arley Forero Rodríguez`  
**Fecha**: `2026-11-17`  
**Modelos / Asistentes Utilizados**: `GPT-6 (conversación de práctica); no se documenta comparación real con otro modelo`

---

## 1. De Prompts Pobres a Técnicas Clásicas de *Prompt Engineering* (Reto 1: `src/triage_rules.py`)

### 1.1 Diagnóstico de un Prompt Pobre y Ambiguo

Prompt evaluado:
> *"El archivo `triage_rules.py` funciona mal con algunos tickets del JSON. Agrégale el equipo recomendado y una clave para duplicados, y no pongas P0 cuando no sea urgente."*

**Tres fallas identificadas durante la práctica:**

1. **Contexto insuficiente:** no especifica qué tickets fallan, cuál es el comportamiento esperado ni qué reglas de negocio deben respetarse; el modelo tendría que inferir los errores de clasificación.
2. **Criterios ambiguos:** expresiones como "equipo recomendado", "clave para duplicados" o "no pongas P0 cuando no sea urgente" no definen los equipos válidos, el formato de la clave ni el impacto técnico que determina P0. La urgencia subjetiva no equivale a indisponibilidad global o fuga multi-tenant.
3. **Falta de verificabilidad:** no establece resultados esperados, invariantes, pruebas ni condiciones de aceptación; no permitiría demostrar que se clasificaron bien los diez casos ni que se preservó la funcionalidad previa.

### 1.2 Uso de *Self-Consistency*, *Chain-of-Thought* y *Few-Shot Prompting*

**Aplicación registrada en la conversación:**

- **Análisis explícito (`<analysis>`):** solicitamos evaluar radio de afectación, disponibilidad/seguridad, expresiones de urgencia y coincidencias entre tickets antes de emitir `<output>`. La respuesta presentó **justificaciones resumidas y comprobables**, no razonamiento interno privado.
- **Casos ambiguos:** `INC-1002` se clasifica P2 por bloqueo individual, aunque diga "hoy"; `INC-1007` se trata como P0 por el acceso reportado a facturas de otras organizaciones (sujeto a verificación técnica); `INC-1009` queda en P2 por una exportación de 20 s que sí finaliza, aunque coincida con un cierre contable.
- **Agrupación:** `INC-1001`/`INC-1006` son duplicados *probables* por error 502 en pagos; `INC-1003`/`INC-1008` se identificaron inicialmente como *relacionados* por lentitud >3 s y volúmenes de más de 10.000 registros. Posteriormente, la implementación determinista les asignó una misma clave de correlación por la categoría común de síntoma: esa clave los agrupa como **candidatos**, sin acreditar una causa raíz compartida.
- **Few-Shot:** el prompt estructurado incluyó ejemplos de cambio visual P3, cuenta individual P2 y saturación de PostgreSQL P1.
- **Self-Consistency:** **no se ejecutaron múltiples consultas independientes con comparación de sus respuestas**. Se realizó una consulta estructurada para los diez incidentes y una revisión posterior mediante código y pruebas automatizadas; estas pruebas no equivalen a Self-Consistency. Una aplicación futura requeriría varias ejecuciones independientes del mismo conjunto, comparación de severidades/claves y revisión de discrepancias.

**Prompt estructurado utilizado, reproducido con los diez incidentes originales:**

```xml
<role>
Actúa como Ingeniero Principal de Confiabilidad (SRE) y Seguridad en IncidentOps, especializado en gestión de incidentes, clasificación de severidad, análisis de impacto y detección de tickets duplicados.
</role>

<domain_rules>
- P0 (SLA 60 min; guardia 24/7): indisponibilidad global de servicio crítico (pagos HTTP 502) o acceso no autorizado/fuga multi-tenant confirmada.
- P1 (SLA 240 min; guardia 24/7): degradación severa de infraestructura compartida con riesgo inminente de caída (p. ej., conexiones de base de datos >90%).
- P2 (SLA 480 min; L-V 08:00–18:00): lentitud sin caída (>3 s), o bloqueo de una sola cuenta.
- P3 (SLA 1440 min; horario hábil): solicitudes cosméticas de UI y mantenimiento preventivo en staging.
¿Por qué? La severidad depende del impacto real en disponibilidad, confidencialidad, integridad y radio de afectación, no de palabras subjetivas como «urgente», «hoy», «necesito» o «me preocupa».
No infieras caída global a partir de un solo comercio; diferencia hechos confirmados de hipótesis.
</domain_rules>

<duplicate_rules>
Compara servicio, síntoma técnico, error y periodo. «Probable» indica coincidencia específica; «relacionado» indica síntomas similares en distintas funciones sin causa común demostrada; «ninguno» cuando no hay evidencia. Para duplicados probables, referencia el ticket anterior. No asumas que una clave común demuestra una misma causa raíz.
</duplicate_rules>

<routing_rules>
payments-platform: pagos; auth-identity: autenticación; reporting-analytics: reportes y exportaciones; frontend-ui: cambios visuales; database-sre: PostgreSQL y conexiones; security-appsec: autorización multi-tenant; devops-platform: TLS y staging. Selecciona un solo equipo principal.
</routing_rules>

<examples>
  <example>
    Input: «El botón de exportar tiene un gris muy claro, sería mejor azul».
    <analysis>Solicitud cosmética; sin caída ni riesgo de seguridad.</analysis>
    <output>severity=P3 | component=frontend-ui | duplicate_of=null | duplicate_status=ninguno</output>
  </example>
  <example>
    Input: «No puedo entrar a mi correo corporativo desde mi celular, urge resolver hoy».
    <analysis>Un único usuario. «Urge» y «hoy» no prueban impacto global.</analysis>
    <output>severity=P2 | component=auth-identity | duplicate_of=null | duplicate_status=ninguno</output>
  </example>
  <example>
    Input: «El pool de conexiones del nodo principal de PostgreSQL alcanzó el 95% y presenta timeouts intermitentes».
    <analysis>Infraestructura compartida >90% y timeouts: riesgo inminente de caída.</analysis>
    <output>severity=P1 | component=database-sre | duplicate_of=null | duplicate_status=ninguno</output>
  </example>
</examples>

<incidents>
[
  {
    "id": "INC-1001",
    "reporter": "carlos.mendoza@clientes-corp.com",
    "created_at": "2026-11-05T08:15:00",
    "raw_text": "URGENTE: El gateway de pagos devuelve HTTP 502 Bad Gateway en todas las transacciones con tarjeta de crédito desde hace 12 minutos. Ningún comercio puede cobrar."
  },
  {
    "id": "INC-1002",
    "reporter": "ana.gomez@clientes-corp.com",
    "created_at": "2026-11-05T09:10:00",
    "raw_text": "He intentado ingresar a mi cuenta tres veces y ahora aparece bloqueada. Necesito acceder hoy mismo porque debo enviar el informe de cierre a la junta directiva."
  },
  {
    "id": "INC-1003",
    "reporter": "soporte-nivel1@incidentops.internal",
    "created_at": "2026-11-05T10:05:00",
    "raw_text": "El dashboard de reportes históricos tarda cerca de 4.5 segundos en cargar cuando un cliente tiene más de 10,000 órdenes registradas. No da error, pero la experiencia es muy lenta."
  },
  {
    "id": "INC-1004",
    "reporter": "luis.torres@logistica-express.co",
    "created_at": "2026-11-05T11:20:00",
    "raw_text": "Sería excelente si pudieran cambiar el color del botón de exportar CSV a verde oscuro porque el gris actual casi no resalta en mi monitor secundario."
  },
  {
    "id": "INC-1005",
    "reporter": "alertas-monitoreo@incidentops.internal",
    "created_at": "2026-11-05T11:45:00",
    "raw_text": "El nodo primario de PostgreSQL muestra un uso de conexiones del 94% y timeouts intermitentes en el pool de conexiones del servicio de facturación."
  },
  {
    "id": "INC-1006",
    "reporter": "maria.rodriguez@retail-latam.com",
    "created_at": "2026-11-05T13:00:00",
    "raw_text": "Otra vez cayó la pasarela de cobros con tarjeta, a nuestros clientes les sale error 502 al intentar pagar el carrito de compras."
  },
  {
    "id": "INC-1007",
    "reporter": "auditoria@seguridad-fin.com",
    "created_at": "2026-11-05T14:30:00",
    "raw_text": "Detectamos que al cambiar el parámetro company_id en la URL del reporte PDF se pueden visualizar facturas pertenecientes a otra organización."
  },
  {
    "id": "INC-1008",
    "reporter": "pedro.sanchez@ventas-norte.com",
    "created_at": "2026-11-05T15:10:00",
    "raw_text": "El listado de planes e historial tarda más de 3 segundos en responder cada vez que abrimos la pestaña de clientes corporativos con más de 10,000 registros."
  },
  {
    "id": "INC-1009",
    "reporter": "elena.vargas@contabilidad-global.com",
    "created_at": "2026-11-05T16:40:00",
    "raw_text": "La exportación mensual a Excel se queda pensando unos 20 segundos pero al final sí descarga el archivo completo. Hoy tenemos cierre contable y nos preocupa que falle más tarde."
  },
  {
    "id": "INC-1010",
    "reporter": "devops-ci@incidentops.internal",
    "created_at": "2026-11-05T17:25:00",
    "raw_text": "El certificado TLS del entorno de staging vencerá en 14 días. Requiere rotación programada antes del próximo sprint."
  }
]
</incidents>

<task>
Para cada uno de los 10 incidentes, en orden de INC-1001 a INC-1010:
1. Examina radio de afectación, disponibilidad, seguridad, expresiones subjetivas y evidencia de coincidencias técnicas.
2. Presenta los criterios verificables en una sección <analysis>; no expongas razonamiento interno privado.
3. Clasifica conforme a <domain_rules> y asigna el componente según <routing_rules>.
4. Emite una sección <output> por incidente con id, severity, sla_minutes, component, duplicate_of y duplicate_status.
5. Solo referencia incidentes anteriores. Usa duplicate_of=null cuando duplicate_status=ninguno; no inventes hechos faltantes.
6. Finaliza con el recuento por severidad y agrupaciones probables/relacionadas.
</task>
```

**Evolución posterior del Reto 1 (implementación):** se solicitó ampliar `TriageResult` y `classify_incident_report` con `recommended_team` restringido a `Backend-Core`, `Platform-SRE`, `Data-DBA` o `Security-IAM`, y `duplicate_group_key` de la forma `<component>:<symptom_category>`. El código refactorizado y las pruebas están en `src/models.py`, `src/triage_rules.py` y `tests/test_triage_rules.py`.

---

## 2. Flujo Explorar → Destilar → Ejecutar en Contexto Limpio (Reto 2: SLA y ADR-002)

### 2.1 Exploración de diseño y destilación (máximo diez líneas)

**Exploración documentada en esta conversación y análisis del código:** alternativas comparadas: (A) diferencia calendario para todos, descartada porque penaliza P2/P3 fuera de jornada; (B) intersección día por día, elegida por simplicidad y costo O(D); (C) calendario externo, pospuesto por alcance y dependencias. Se identificaron cierres en fin de semana, creación fuera de ventana, varios días, umbrales y estado resuelto.

**Resumen destilado utilizado para implementar (9 líneas):**

> 1. P0/P1 consumen tiempo calendario continuo (24/7); P2/P3 solo lunes–viernes 08:00–18:00.  
> 2. Para P2/P3, sumar intersecciones de intervalos con cada jornada hábil; O(D), O(1) memoria.  
> 3. Sábado/domingo y noches no consumen SLA, aunque el ticket exista.  
> 4. Viernes 18:30 a lunes 08:30 equivale a 30 minutos hábiles.  
> 5. Acumular segundos y convertir a minutos completos solo al final.  
> 6. Mantener `is_breached` cuando `elapsed_minutes > allowed_minutes` (semántica existente).  
> 7. `requires_escalation` desde 75% y durante todo incumplimiento abierto.  
> 8. Un resuelto usa `resolved_at`, no escala, pero conserva incumplimiento histórico.  
> 9. Documentar límites: sin festivos; fechas en horario local consistente, sin transición DST.

### 2.2 Prompt XML con contexto curado y ejecución del diseño

Este es el prompt **reproducible preparado a partir de la decisión destilada y empleado como especificación de trabajo en este desarrollo**. Se documenta que **no se abrió efectivamente un nuevo chat independiente**; el requisito metodológico de comparar una ejecución en contexto completamente limpio sigue pendiente de realización por el estudiante.

```xml
<context>
Proyecto IncidentOps; archivo src/sla_calculator.py, modelos Incident,
SLARule y SLAEvaluation de src/models.py, tabla SLA_POLICY_TABLE.
Contexto técnico mínimo recuperable:
  evaluate_sla_status(incident: Incident, reference_time: datetime) -> SLAEvaluation
  P0: max_resolution_minutes=60, operates_24x7=True
  P1: max_resolution_minutes=240, operates_24x7=True
  P2: max_resolution_minutes=480, operates_24x7=False
  P3: max_resolution_minutes=1440, operates_24x7=False
  escalation_threshold_ratio=0.75
Documento de referencia: docs/adr/000-template.md.
El bloque AST que emula LSP está en evidence/context_audit_sla.txt.
</context>
<decision_summary>
P0/P1 calendario; P2/P3 L-V de 08:00 a 18:00 sumando intersecciones
por día (O(D), memoria O(1)). Fuera de jornada: cero.
Escalar desde 75% aun cuando el ticket sigue abierto e incumplido.
En RESOLVED usar resolved_at, conservar breach histórico, no escalar.
</decision_summary>
<constraints>
Mantener firmas, tipos y SLARule; cero dependencias nuevas.
No introducir feriados ni calendario por cliente.
Preservar comparación is_breached por minutos completos > máximo.
Validar fechas, consistencia de zona horaria y límites 08:00/18:00.
Casos de prueba verificables con resultados numéricos y sin supuestos ocultos.
</constraints>
<task>
1. Escribir docs/adr/002-calculo-sla-horario-habil.md siguiendo ADR-000,
   con opciones, elección, trade-offs y diagrama Mermaid.
2. Refactorizar src/sla_calculator.py con el algoritmo aceptado.
3. Añadir pruebas para creación en sábado, viernes 18:30,
   cruces de fines de semana, P0/P1 24/7, umbral 75%, breach
   y RESOLVED; ejecutar pruebas y conservar evidencias.
</task>
```

**Resultado verificado:** ADR en `docs/adr/002-calculo-sla-horario-habil.md`, módulo en `src/sla_calculator.py`, 16 pruebas nuevas de SLA en `tests/test_sla_calculator.py`, más 4 de triaje (total 20 aprobadas). Salidas en `evidence/`.

**Casos representativos comprobados (fecha de noviembre 2026):**

| Severidad | Inicio → Evaluación | Minutos esperados/observados |
| :-- | :-- | --: |
| P2 | Vie 06 17:00 → Lun 09 09:00 | 120 / 120 |
| P2 | Vie 06 18:30 → Lun 09 08:30 | 30 / 30 |
| P3 | Sáb 07 12:00 → Lun 09 09:00 | 60 / 60 |
| P2 | Lun 09 16:00 → Mar 10 12:00 | 360 / 360 |
| P0 | Vie 06 17:00 → Lun 09 09:00 | 3840 / 3840 |
| P1 | Lun 09 08:00 → Lun 09 11:00 | 180 / 180 |

---

## 3. Tipos de Modelos y Matriz de Decisión Arquitectónica

### 3.1 Comparación de tipos de modelos

**Observación real:** la práctica aquí se desarrolló con **GPT-6**. No se realizó una segunda ejecución con Flash, Mini, Haiku ni con otro ajuste de razonamiento. **No existe base empírica para afirmar cuál modelo fue superior o indispensable.**

**Hipótesis a contrastar, no resultado observado:** un modelo rápido puede bastar para formatear XML, diagnosticar ambigüedades evidentes y tabular reportes; el razonamiento extendido podría beneficiar el diseño de reglas con múltiples casos borde, los trade-offs del ADR y la validación de invariantes. La necesidad de razonamiento adicional se verifica con pruebas y no se infiere del nombre del modelo.

**Protocolo pendiente para comparación empírica:** enviar el mismo prompt, el mismo bloque de contexto y los mismos casos a ambos modos/modelos en chats separados; comparar resultados exactos de 10 severidades, claves de duplicación, casos SLA, fallos, latencia y costo cuando esté disponible; anotar diferencias sin asumir equivalencia de condiciones.

### 3.2 Matriz de decisión arquitectónica

| Escenario / Requerimiento | Paradigma elegido | Justificación técnica |
| :-- | :-- | :-- |
| Contabilizar minutos hábiles y verificar el 75% de SLA | **Código determinista** | Las reglas son explícitas, auditables, reproducibles, baratas, de latencia reducida y sin alucinación. |
| Explorar casos borde y redactar un ADR antes de alterar consultas SQL | **Asistente GenAI en chat** | Ayuda a comparar opciones, descubrir casos no obvios y documentar; salida revisada por humanos y validada con pruebas, no ejecutada automáticamente. |
| Detectar anomalías numéricas en millones de métricas CPU/RAM por minuto | **ML clásico** | Detección estadística de patrones/anomalías a escala con inferencia ligera; controlar deriva, falsos positivos y calidad de datos. |
| Clasificar texto libre con patrones nuevos que no cubren heurísticas | **LLM en tiempo de ejecución** | Flexible para lenguaje abierto; costo y latencia mayores y riesgo de clasificación inconsistente. Requiere salida validada, observabilidad, límites de confianza y ruta determinista/fallback. |

---

## 4. Economía de Tokens y Curaduría de Contexto

### 4.1 Auditoría de símbolos

**Advertencia metodológica:** las cifras de tokens siguientes proceden del fallback `estimador-bpe-local` de `src/context_audit.py`; **NO son mediciones `tiktoken o200k_base`**, porque no fue posible instalar `tiktoken` en este entorno sin red. Los caracteres sí corresponden a conteos exactos de las cargas de texto definidas por el auditor. El nivel semántico es una **emulación AST de operaciones LSP**, no una conexión con un servidor LSP. Estos valores deben reemplazarse por una ejecución real con `uv run` y `tiktoken` disponible antes de declarar completado el requisito de medición exacta.

**Símbolo: `classify_incident_report`**

| Estrategia de recolección | Alcance | Caracteres | Tokens aproximados (NO tiktoken) | Reducción estimada vs. fuerza bruta |
| :-- | :-- | --: | --: | --: |
| Fuerza bruta (`glob` + `read`) | 9 archivos incluidos en el auditor | 40318 | 15207 | 0% |
| Búsqueda textual (`grep` + `read`) | 2 archivos `.py` | 7977 | 2988 | 80,4% |
| Semántica (`AST`, estilo LSP) | Definiciones, tipos y referencias | 2984 | 1038 | 93,2% |

**Símbolo: `evaluate_sla_status`**

| Estrategia de recolección | Alcance | Caracteres | Tokens aproximados (NO tiktoken) | Reducción estimada vs. fuerza bruta |
| :-- | :-- | --: | --: | --: |
| Fuerza bruta (`glob` + `read`) | 9 archivos incluidos en el auditor | 40318 | 15207 | 0% |
| Búsqueda textual (`grep` + `read`) | 4 archivos `.py` | 25190 | 9073 | 40,3% |
| Semántica (`AST`, estilo LSP) | Definiciones, tipos y referencias | 5316 | 1730 | 88,6% |

Nota: el conjunto «fuerza bruta» es el definido en el script (`src/*.py`, `data/*.json`, `docs/adr/*.md`), **no** el repositorio completo incluyendo pruebas y bitácora. Los porcentajes se recalcularán con el tokenizador exacto al disponer de dependencias.

### 4.2 Formatos de serialización de los diez incidentes

| Formato | Caracteres | Tokens aproximados (NO tiktoken) |
| :-- | --: | --: |
| JSON indentado | 2942 | 1206 |
| JSON compacto | 2641 | 1105 |
| YAML equivalente (generado por el auditor) | 2579 | 983 |
| Texto delimitado por `\|` (etiquetado CSV por auditor) | 2171 | 842 |

**Decisión de serialización:** para datos tabulares homogéneos, el formato compacto o delimitado puede reducir gasto de contexto, siempre que preserve el escape de delimitadores y saltos de línea. Para registros abiertos con texto variable, JSON compacto resulta más robusto y estructuralmente inequívoco; JSON indentado favorece inspección humana. El «YAML equivalente» y el «CSV delimitado» producidos por el script son representaciones simplificadas, no serializaciones plenamente escapadas en todos los casos; no deben consumirse como garantía de reversibilidad. La elección final requiere medición real con `tiktoken` y pruebas de round-trip.

**Reproducción de medición exacta al disponer de dependencias:**

```bash
uv sync
uv run python -m src.context_audit --symbol classify_incident_report
uv run python -m src.context_audit --symbol evaluate_sla_status
uv run python -m src.context_audit --compare-formats
```

Revisar la línea `Tokenizador activo: tiktoken (o200k_base)` en las tres salidas; repetir las tablas con los valores reportados. Si aparece `estimador-bpe-local`, la medición exacta sigue pendiente.

---

## 5. Entregables, resultados y transparencia

| Evidencia / entregable | Estado |
| :-- | :-- |
| Reto 1: `src/models.py`, `src/triage_rules.py` | Implementado; 4 pruebas aprobadas |
| Reto 2: `src/sla_calculator.py` | Implementado; 16 pruebas aprobadas |
| `docs/adr/002-calculo-sla-horario-habil.md` | Creado con diagrama Mermaid |
| `CONTEXT_LOG.md` | Diligenciado con distinción entre hechos y pendientes |
| Auditorías de contexto y formatos | Ejecutadas con **estimación**, sin `tiktoken` |
| Comparación de modelos rápidos/extendidos | **Pendiente de ejecución real** |
| Self-Consistency en chats nuevos independientes | **Pendiente de ejecución real** |
| Ejecución del Reto 2 en chat limpio independiente | **Pendiente de ejecución real** |

**Verificación efectivamente realizada:** `python -m unittest discover -s tests -v` → **20/20 pruebas aprobadas**; `python -m src.triage_rules` y `python -m src.sla_calculator` → salidas registradas en `evidence/`. La ejecución con `uv run` no se completó porque falló la instalación de `tiktoken` por falta de red. Los archivos de `evidence/` registran el método utilizado.
