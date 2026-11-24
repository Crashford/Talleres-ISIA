# Evidencias de ejecución — Semana 1 (históricas)

- test_run.txt: ejecución local de unittest (20 pruebas).
- triage_demo.txt, sla_demo.txt: salidas históricas de ambos módulos.
- context_audit_classify.txt, context_audit_sla.txt y context_audit_formats.txt: salidas históricas del auditor.

La auditoría de Semana 1 se ejecutó sin tiktoken; sus estimaciones BPE no son mediciones exactas. Se emuló LSP mediante AST, sin iniciar un servidor LSP. No se ejecutó comparación empírica de modelos ni sesiones independientes de Self-Consistency.

En Semana 2 las rutas del dominio cambiaron. Para repetir las verificaciones:

```bash
uv sync
uv run pytest -v
uv run python -m src.domain.triage_rules
uv run python -m src.domain.sla_calculator
uv run python -m src.context_audit --symbol classify_incident_report
uv run python -m src.context_audit --symbol evaluate_sla_status
uv run python -m src.context_audit --compare-formats
```

La evidencia histórica no certifica la implementación H001.
