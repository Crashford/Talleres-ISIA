---
name: adr-writer
description: Redacta y valida ADR (Architecture Decision Records) de IncidentOps con la plantilla MADR estricta; úsala bajo demanda para crear o revisar un ADR, comparar alternativas arquitectónicas o registrar una decisión estructural difícil de revertir.
---

# Registro de decisiones arquitectónicas

- Leer `docs/adr/000-template.md` y los ADR existentes antes de escribir. Copiar la estructura MADR sin renombrar ni añadir secciones: título `# ADR-NNN: ...`, metadatos, `---`, `## 1. Contexto y Problema`, `## 2. Opciones Consideradas`, `## 3. Decisión Arquitectónica` y `## 4. Consecuencias y Trade-offs`, separadas por `---`.
- Incluir siempre los metadatos: **Estado** (`Propuesto | Aceptado | Reemplazado por ADR-XXX`), **Fecha** (YYYY-MM-DD de la decisión), **Autor(es)** reales, **Reemplaza a** (opcional) y **Reemplazado por** (opcional; `—` si no aplica).
- Un archivo = una decisión arquitectónica estructural y difícil de revertir. Si surgen dos decisiones, separarlas en ADR distintos; no mezclar reglas de negocio, criterios de prueba ni detalle de implementación.
- Historial append-only: crear el siguiente ADR numerado sin reescribir ni borrar los anteriores. Para registrar una sustitución, actualizar únicamente el puntero de metadatos `Reemplazado por` del ADR previo; conservar intactos su contexto, decisión y consecuencias.
- En `Opciones Consideradas`, documentar al menos dos alternativas arquitectónicas reales y viables, cada una con ventajas y desventajas auténticas, incluido el costo de la opción elegida. Prohibidas las opciones de relleno; justificar la elección en la sección 3.
- Diagramas Mermaid opcionales solo en la sección 3 y exclusivamente para capas, fronteras, dependencias o topologías estáticas; etiquetar el sentido de las dependencias. Prohibidos los diagramas de flujo algorítmicos con decisiones `if/else`, bucles o secuencias temporales.
- No incluir enlaces frágiles ni inventario de «Componentes Afectados», rutas de código, listas tácticas de comandos, escenarios BDD Given/When/Then, requisitos duplicados de `spec.md` ni listas de tareas de implementación de `plan.md`.
- Antes de entregar, verificar: plantilla idéntica, cinco metadatos, una sola decisión, al menos dos opciones reales, consecuencias positivas y negativas, y ausencia de los contenidos prohibidos.
