# Research — H002

Decisiones técnicas aprobadas por el usuario antes de Build:

| Decisión | Justificación / alternativas |
|---|---|
| Mantener SQLite3 con INNER JOIN y filtrado SQL | ADR-001 y guía. Evita N+1 sin ORM; no cambiar motor. |
| DATABASE_URL por defecto sqlite:///:memory: | Exigencia de la guía. Sin datos, devuelve vacío; no sembrar automáticamente. Para compartir datos entre procesos REST y CLI se usa un archivo SQLite explícito. |
| Tiempo ISO 8601 opcional | Aceptar fecha-hora (con o sin offset), no fechas sin hora ni números. Preservar la semántica ADR-002: no mezclar naive/aware en una evaluación explícita; P2/P3 requieren el mismo offset; fecha anterior a creación es inválida. Sin referencia explícita, tomar un solo instante actual y expresarlo según la convención de cada incidente (naive local del runtime o aware en su zona). No interpretar el instante como consulta histórica de estados. |
| Orden estable por incident_id, filtro exacto | Paridad reproducible sin introducir paginación ni búsqueda parcial; componente desconocido retorna vacío. Filtro vacío/espacios se rechaza como entrada inválida; no equivale a ausencia. |
| Puerto completo con correlación opcional | La guía pide save/get/find/list/check_health en H002. El modelo heredado carece de clave persistida; proponer columna nullable y argumento opcional de save, sin generación retroactiva ni endpoint de registro/detección. find_open_duplicates consulta OPEN/IN_PROGRESS, sin confirmación causal. |
| Ciclo de vida de conexión por operación | Evita compartir conexión SQLite entre hilos de FastAPI y garantiza cierre; pruebas REST/CLI usan archivo temporal común. El puerto es inyectable. |
| Ruff jerárquico | TID251/TID252 cubren imports definidos; no se afirma que por sí solos prueben toda la arquitectura. Complementar con revisión de imports y regresiones. |

Las decisiones fueron aprobadas antes de Build e implementadas en el commit 3084195; CI confirmó la verificación.
