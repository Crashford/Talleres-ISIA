# Evidencia H001 — 2026-11-24

## Código verificado
Commit f3bc209e92354d6973b7077ef1bec957c07b8026, rama practica-guiada-sdd-semana-2.
Implementación: b3468682bde8fa607c12646489d9f577cb2d9d54.

## Verificación local
Se reconstruyó una copia local de los módulos necesarios, pruebas y datos de muestra. Los hashes Git de todos esos archivos coincidieron con los blobs publicados. No se clonó el repositorio (sin acceso directo de red) ni se ejecutó uv localmente.
Python 3.13.5; pytest 9.0.2; FastAPI 0.128.2; Pydantic 2.13.5; Typer 0.26.3; httpx 0.28.1.

Comando: python -m pytest -v
Resultado: 34 passed, 10 subtests passed in 0.16s.
- 14 casos parametrizados BDD H001.
- 16 pruebas de regresión SLA.
- 4 pruebas de regresión triaje; 10 subpruebas de clasificación.

Comando: python -m src.adapters.inbound.cli triage --incident-id INC-1001 --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"
Salida:
```json
{"incident_id":"INC-1001","severity":"P0","component":"payments-gateway","rationale":"Fallo HTTP 502 en servicio crítico de pagos: P0 preventivo; alcance global por confirmar.","consistency_ratio":1.0,"recommended_team":"Backend-Core","duplicate_group_key":"payments-gateway:http-502-outage"}
```
Los módulos src.domain.triage_rules (10 casos) y src.domain.sla_calculator (6 demostraciones con aserciones) también terminaron correctamente.

## CI con uv
Ejecución confirmada por GitHub: https://github.com/Crashford/Talleres-ISIA/actions/runs/45487124921
Ambos jobs verify (3.10) y verify (3.12) concluyeron success. Pasos exitosos: uv sync, uv run pytest -v, motores de dominio, CLI, benchmark 10.000 registros, auditoría de contexto y carga de artefacto uv.lock.
Artefactos uv-lock-python-3.10 y uv-lock-python-3.12 disponibles en esa ejecución. El lockfile de la rama aún corresponde a Semana 1; uv sync lo regeneró en CI. Pendiente versionar el lockfile actualizado (uv lock) para reproducibilidad bloqueada.

## Alcance metodológico
Se siguieron los contratos y orden Plan → Build con aprobaciones humanas en chat. OpenCode /init y sus modos no fueron ejecutados en una sesión real de OpenCode. Esta evidencia no acredita una sesión de OpenCode ni la ejecución de GitHub Spec Kit.
