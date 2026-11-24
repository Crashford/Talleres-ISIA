# ADR-001: Persistencia SQLite con consultas relacionales optimizadas

- **Estado**: Aceptado (implementación pendiente en H002)
- **Fecha**: 2026-11-24
- **Autor(es)**: Equipo IncidentOps (decisión aprobada por el usuario; redacción asistida)

---

## 1. Contexto y Problema

El repositorio heredado usa SQLite3 estándar y tiene un benchmark con 10.000 registros. El resumen carga todas las filas, filtra en Python y consulta las políticas de SLA por incidente (N+1). La práctica requiere consultas filtradas eficientes sin agregar infraestructura ni ORM pesado. Este ADR se registra hoy para cubrir la decisión ausente en Semana 1; no acredita una optimización previa.

---

## 2. Opciones Consideradas

1. **Opción A — SQLite con escaneo y filtrado en memoria**:
   - *Ventajas*: simplicidad y escasa infraestructura.
   - *Desventajas*: transferencia innecesaria de filas y consultas N+1.
2. **Opción B — SQLite relacional con filtrado SQL, JOIN e índice compuesto**:
   - *Ventajas*: reduce filas transferidas y viajes a la base de datos; conserva stdlib y ejecución local.
   - *Desventajas*: costo de mantenimiento del índice y necesidad de validar el esquema.

---

## 3. Decisión Arquitectónica

Adoptar la opción B. Conservar SQLite3 estándar, consultas parametrizadas, filtrado por estado/componente, INNER JOIN con las políticas de SLA y un índice compuesto (component, status). El cálculo de SLA sigue siendo responsabilidad del dominio. Un cambio de motor requiere un nuevo ADR.

---

## 4. Consecuencias y Trade-offs

- **Positivas**: menor sobrecarga de consultas, reproducibilidad y dependencia mínima.
- **Negativas / Trade-offs**: el índice consume espacio y añade costo de escritura; SQLite tiene límites de concurrencia que deberán evaluarse en futuras entregas. La mejora de rendimiento debe medirse, no se presupone.
