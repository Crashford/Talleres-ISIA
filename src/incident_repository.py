"""Benchmark de Semana 1 sobre el adaptador optimizado del H002."""

import argparse
import time
from datetime import datetime

from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.services import IncidentService
from contextlib import nullcontext


def _run_benchmark() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de resumen SQLite")
    parser.add_argument("--records", type=int, default=10000)
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    if args.records < 0 or args.iterations < 1:
        parser.error("records debe ser >= 0 e iterations >= 1")
    with SQLiteIncidentRepository() as repo:
        print(f"Sembrando {args.records} incidentes en SQLite en memoria...")
        repo.seed_synthetic_incidents(args.records)
        service = IncidentService(lambda: nullcontext(repo))
        ref_time = datetime(2026, 11, 20, 12)
        start = time.perf_counter()
        for _ in range(args.iterations):
            result = service.get_active_incidents_summary("payments-gateway", ref_time)
        elapsed_ms = (time.perf_counter() - start) * 1000
        print("=== Resultado del Benchmark (Después de Refactorizar) ===")
        print(f"Incidentes activos encontrados para 'payments-gateway': {result.total_active}")
        print(f"Tiempo total ({args.iterations} ejecuciones sobre {args.records} filas): {elapsed_ms:.2f} ms")
        print(f"Promedio por consulta: {elapsed_ms / args.iterations:.2f} ms")
        print("Consulta SQL parametrizada con INNER JOIN e índice (component, status).")


if __name__ == "__main__":
    _run_benchmark()
