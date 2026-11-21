# Bitácora de Ingeniería de Prompts y Contexto — Semana 1 (`CONTEXT_LOG.md`)

**Estudiante(s)**: `[Nombre completo]`  
**Fecha**: `[YYYY-MM-DD]`  
**Modelos / Asistentes Utilizados**: `[Ej. Claude 4.5/5, GPT-4o/5, Gemini 2.5 Pro/Flash, etc.]`

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

## 2. Flujo Explorar $\rightarrow$ Destilar $\rightarrow$ Ejecutar en Contexto Limpio (Reto 2: Cálculo de SLA en Horario Hábil y ADR-002)

### 2.1 Exploración de Diseño (Sin Generar Código Aún) y Destilación
- **Objetivo explorado**: Diseño del algoritmo de cálculo de SLA en horario hábil (`P2`/`P3`, Lunes–Viernes 08:00–18:00) vs. 24/7 (`P0`/`P1`) y regla de escalamiento preventivo al 75%.
- **Síntesis de tu exploración de alternativas y resumen destilado (máx. 10 líneas)**:
  > `[Describe qué dudas e hipótesis iniciales exploraste, qué casos borde descubriste junto con el modelo (creación en fin de semana, fuera de horario, cruces de varios días) y pega el bloque destilado que llevaste al nuevo chat limpio]`

### 2.2 Ejecución con Contexto Curado en Nuevo Chat Limpio (*Context Engineering*)
Copia el prompt estructurado con etiquetas XML que utilizaste en un nuevo chat limpio para generar el **ADR (`docs/adr/002-calculo-sla-horario-habil.md`)** y la refactorización de `src/sla_calculator.py`:

```xml
<!-- Pega aquí tu prompt estructurado con <context>, <decision_summary>, <constraints>, <task> -->
```

---

## 3. Tipos de Modelos y Matriz de Decisión Arquitectónica

### 3.1 Comparación de Tipos de Modelos
Compara el comportamiento que observaste al interactuar con:
1. **Modelo Rápido / Estándar (ej. Flash, Mini, Haiku o modo estándar)**:
2. **Modelo de Razonamiento Extendido (*Thinking Model*)**:
- ¿En cuál de las tareas de la semana fue indispensable el modelo de razonamiento y en cuál bastó el modelo rápido?

### 3.2 Matriz de Decisión Arquitectónica
Para la plataforma *IncidentOps* y su evolución futura, justifica qué paradigma es el adecuado en cada escenario:

| Escenario / Requerimiento | Paradigma Elegido (Código Determinista / ML Clásico / Asistente GenAI en Chat / LLM en Tiempo de Ejecución) | Justificación Técnica (Determinismo, Costo, Latencia, Riesgo de Alucinación) |
| :--- | :--- | :--- |
| 1. Contabilizar minutos hábiles transcurridos y verificar si un ticket superó el 75% de su SLA | | |
| 2. Explorar casos borde y redactar un ADR antes de modificar la arquitectura de consultas SQL | | |
| 3. Detectar anomalías numéricas en millones de métricas de CPU/RAM por minuto | | |
| 4. Clasificar reportes de incidentes redactados en lenguaje natural abierto cuando las reglas deterministas no cubren nuevos patrones | | |

---

## 4. Economía de Tokens y Curaduría de Contexto con `tiktoken` (LSP vs. `grep`/`read` vs. `glob`/`read`)

### 4.1 Medición Empírica en *IncidentOps*
Completa la tabla con los resultados obtenidos al auditar los símbolos con `uv run python -m src.context_audit --symbol evaluate_sla_status` (y `classify_incident_report`):

| Estrategia de Recolección de Contexto | Alcance (Archivos / Nodos) | Caracteres Totales | Tokens (`tiktoken o200k_base`) | % de Reducción vs. Fuerza Bruta |
| :--- | :--- | :---: | :---: | :---: |
| **1. Fuerza Bruta (`glob` + `read` todo)** | Todos los archivos del proyecto | | | 0% (Línea base) |
| **2. Búsqueda Textual (`grep` + `read` `.py`)** | Archivos `.py` donde aparece el símbolo | | | |
| **3. Semántica vía LSP (`definition` + `references` + `hover`)** | Solo definición, tipos asociados y líneas de invocación | | | |

### 4.2 Comparación de Formatos de Serialización (`--compare-formats`)
Registra los tokens medidos con `tiktoken` para los 10 incidentes en JSON indentado, JSON compacto, YAML y CSV, y explica qué formato elegirías al inyectar datos tabulares o logs largos en la ventana de contexto.
