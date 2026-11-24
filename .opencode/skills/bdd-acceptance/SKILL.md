---
name: bdd-acceptance
description: Redacta especificaciones y pruebas de aceptación Given/When/Then para los hitos IncidentOps; asegura trazabilidad de escenarios, paridad REST/CLI y almacenamiento aislado.
---

# Aceptación BDD

- Describir el comportamiento observable con vocabulario ubicuo de negocio: Given establece contexto, When expresa una acción y Then indica resultados observables. Evitar clases Python y tablas SQL en los escenarios.
- Cada escenario de spec.md tiene un identificador y una función test_bdd_* correspondiente en tests/. Parametrizar casos borde cuando representen el mismo comportamiento.
- Preparar pruebas de aceptación antes de implementar el nuevo caso de uso; confirmar que fallan por la funcionalidad ausente y después que pasan.
- Para REST usar fastapi.testclient.TestClient; para CLI, typer.testing.CliRunner. Comparar JSON completo cuando se exige paridad; verificar estado HTTP y código de salida.
- Usar repositorios aislados por prueba: tmp_path para compartir persistencia entre interfaces, o SQLite en memoria con ciclo de vida controlado. Nunca utilizar datos reales o una base de producción.
- Fijar reference_time para pruebas SLA; cubrir estados activos, excluidos, filtros, vacío, incumplimiento y escalamiento según especificación. No replicar el algoritmo del dominio en las expectativas.
- Ejecutar `uv run pytest -v`; conservar las regresiones de hitos anteriores. Registrar resultados reales y no marcar tareas verificadas sin evidencia.
