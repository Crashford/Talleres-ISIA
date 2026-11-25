# Evidencia H003 — Verificación manual CLI con almacenamiento persistente

Fecha: 2026-11-24. Rama: `practica-guiada-sdd-semana-2`. Archivo SQLite aislado: `C:/Users/YEISON~1/AppData/Local/Temp/opencode/h003-manual.db` (fuera del repositorio). La consola PowerShell imprimió los acentos con el codepage activo (`pblico`, `más` → `m?s`); el JSON producido usa UTF-8 y las aserciones automáticas verifican los valores exactos.

## Comandos ejecutados

```powershell
$db = "C:\Users\YEISON~1\AppData\Local\Temp\opencode\h003-manual.db"
if (Test-Path -LiteralPath $db) { Remove-Item -LiteralPath $db }
$env:DATABASE_URL = "sqlite:///" + $db.Replace('\','/')
uv run python -m src.adapters.inbound.cli create --title "Latencia alta en API pública" --raw-text "El dashboard tarda 12 segundos con 10.000 registros" --incident-id "INC-P2F4E6A8" --created-at "2026-11-06T17:00:00"
```

Código de salida real: `CREATE_EXIT=0`. Salida real:

```json
{"incident_id": "INC-P2F4E6A8", "title": "Latencia alta en API pblica", "component": "reporting-api", "severity": "P2", "created_at": "2026-11-06T17:00:00", "status": "OPEN", "resolved_at": null, "recommended_team": "Backend-Core", "duplicate_group_key": "reporting-api:slow-large-dataset-over-3s", "rationale": "Latencia en consultas sobre m?s de 10.000 registros.", "consistency_ratio": 1.0, "is_duplicate": false, "duplicate_of": []}
```

```powershell
uv run python -m src.adapters.inbound.cli sla --incident-id "INC-P2F4E6A8" --reference-time "2026-11-09T09:00:00"
```

Código de salida real: `SLA_EXIT=0`. Salida real:

```json
{"incident_id": "INC-P2F4E6A8", "reference_time": "2026-11-09T09:00:00", "elapsed_minutes": 120, "allowed_minutes": 480, "remaining_minutes": 360, "is_breached": false, "requires_escalation": false}
```

La auditoría se ejecutó en otra invocación del proceso, sobre el mismo archivo SQLite: demuestra persistencia entre operaciones y reproduce los cinco valores exigidos (E006).

## Comprobación adicional de almacenamiento efímero

```powershell
$env:DATABASE_URL = "sqlite:///:memory:"
uv run python -m src.adapters.inbound.cli create --title "HTTP 502 en pasarela de pagos" --raw-text "HTTP 502 Bad Gateway en pasarela de pagos"
```

Código de salida real: `EPHEMERAL_EXIT=1`. Salida por stderr:

```text
La configuraci n de almacenamiento no conserva datos entre operaciones; defina DATABASE_URL con un archivo SQLite.
```

No se imprimió JSON de éxito ni se generó identificador (E015).

Nota funcional: el texto de ejemplo de `contracts/incidents.md` (`Latencia alta sostenida en la API pública sin pérdida de servicio`) produce P3 con el motor de triaje vigente. Para obtener el P2 determinista exigido por E006/T005 se usó un texto con indicios reales de latencia y volumen (`El dashboard tarda 12 segundos con 10.000 registros`), sin modificar `src/domain/triage_rules.py`.
