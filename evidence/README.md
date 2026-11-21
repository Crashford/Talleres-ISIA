# Evidencias de ejecución — 2026-11-17

- `test_run.txt`: ejecución local de `python -m unittest discover -s tests -v` (20 pruebas).
- `triage_demo.txt` y `sla_demo.txt`: salida de ambos módulos en Python.
- `context_audit_classify.txt`, `context_audit_sla.txt` y `context_audit_formats.txt`: salidas del auditor.

**Limitación importante**: la auditoría de tokens se ejecutó SIN `tiktoken` porque esta dependencia no estaba disponible en el entorno y la descarga de paquetes no tuvo acceso a red. El módulo usa explícitamente `estimador-bpe-local`, así que los valores incluidos son **aproximaciones, NO mediciones exactas de `tiktoken o200k_base`**. Se incluyen caracteres exactos y la forma de repetir la medición después de instalar dependencias.

```bash
uv sync
uv run python -m src.context_audit --symbol classify_incident_report
uv run python -m src.context_audit --symbol evaluate_sla_status
uv run python -m src.context_audit --compare-formats
uv run python -m unittest discover -s tests -v
```

La implementación extrae contexto semántico mediante AST que **emula** definición, hover y referencias de LSP; no se inició un servidor LSP. No se ejecutó comparación empírica de modelos diferentes ni sesiones independientes de Self-Consistency. Ninguna de estas evidencias se presenta como realizada.
