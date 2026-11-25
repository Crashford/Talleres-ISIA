"""Aceptación H002 y contrato del adaptador SQLite."""

import json
import sqlite3
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.adapters.inbound.api.app import create_app
from src.adapters.inbound.cli import app
from src.adapters.outbound.factory import repository_factory
from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.ports import IncidentRepositoryPort
from src.domain.models import Incident

REF = "2026-11-09T10:00:00"
ENDPOINT = "/api/v1/incidents/summary"


def make_incident(ident, component="payments-gateway", severity="P0",
                  status="OPEN", created="2026-11-09T08:00:00", resolved=None):
    return Incident(ident, f"Reporte {ident}", component, severity, status,
                    datetime.fromisoformat(created),
                    datetime.fromisoformat(resolved) if resolved else None)


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    db = tmp_path / "incidents.db"
    url = "sqlite:///" + str(db)
    monkeypatch.setenv("DATABASE_URL", url)
    with repository_factory() as repo:
        repo.save_incident(make_incident("A"), "payments-gateway:http-502-outage")
        repo.save_incident(make_incident("B", "auth-identity", "P2", "IN_PROGRESS",
                                         "2026-11-09T09:00:00"))
        repo.save_incident(make_incident("C", status="RESOLVED",
                                         resolved="2026-11-09T09:00:00"))
        repo.save_incident(make_incident("D", status="ESCALATION_REQUIRED"))
    with TestClient(create_app()) as client:
        yield client


def test_bdd_global_summary(seeded):
    result = seeded.get(ENDPOINT, params={"reference_time": REF})
    assert result.status_code == 200
    assert result.json() == {
        "total_active": 2, "breached_count": 1, "incidents": [
            {"incident_id": "A", "title": "Reporte A", "component": "payments-gateway",
             "severity": "P0", "status": "OPEN", "elapsed_minutes": 120,
             "is_breached": True, "requires_escalation": True},
            {"incident_id": "B", "title": "Reporte B", "component": "auth-identity",
             "severity": "P2", "status": "IN_PROGRESS", "elapsed_minutes": 60,
             "is_breached": False, "requires_escalation": False},
        ],
    }


def test_bdd_component_filter(seeded):
    response = seeded.get(ENDPOINT, params={"component": "auth-identity", "reference_time": REF})
    assert response.status_code == 200
    data = response.json()
    assert data["total_active"] == 1 and data["breached_count"] == 0
    assert [item["incident_id"] for item in data["incidents"]] == ["B"]


@pytest.mark.parametrize("component", [None, "unknown"])
def test_bdd_empty_summary(tmp_path, monkeypatch, component):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "empty.db"))
    params = {"reference_time": REF}
    if component is not None:
        params["component"] = component
    with TestClient(create_app()) as client:
        response = client.get(ENDPOINT, params=params)
    assert response.status_code == 200
    assert response.json() == {"total_active": 0, "breached_count": 0, "incidents": []}


def test_bdd_cli_summary_parity(seeded, runner):
    params = {"component": "payments-gateway", "reference_time": REF}
    result = runner.invoke(app, ["summary", "--component", params["component"],
                                 "--reference-time", REF])
    assert result.exit_code == 0, result.output
    response = seeded.get(ENDPOINT, params=params)
    assert response.status_code == 200
    assert json.loads(result.stdout) == response.json()


@pytest.mark.parametrize("params", [
    {"reference_time": "2026-11-09"}, {"reference_time": "123"},
    {"reference_time": "2026-11-09T07:00:00"},
    {"reference_time": "2026-11-09T10:00:00Z"}, {"component": "  "},
])
def test_invalid_summary_http(seeded, params):
    assert seeded.get(ENDPOINT, params=params).status_code == 422


@pytest.mark.parametrize("args", [
    ["--reference-time", "bad"], ["--component", " "],
])
def test_invalid_summary_cli(seeded, runner, args):
    result = runner.invoke(app, ["summary", *args])
    assert result.exit_code == 1
    assert not result.stdout.strip()
    assert result.stderr.strip()


def test_unknown_component_on_populated_storage(seeded):
    response = seeded.get(ENDPOINT, params={"component": "unknown", "reference_time": REF})
    assert response.status_code == 200
    assert response.json() == {"total_active": 0, "breached_count": 0, "incidents": []}


def test_repository_port_and_sql(tmp_path):
    with SQLiteIncidentRepository(str(tmp_path / "contract.db")) as repo:
        assert isinstance(repo, IncidentRepositoryPort)
        assert repo.check_health()
        a = make_incident("A")
        a.duplicate_group_key = "key"
        repo.save_incident(a)
        repo.save_incident(make_incident("B", status="RESOLVED", resolved=REF), "key")
        assert repo.get_incident("A") == a
        assert repo.get_incident("missing") is None
        assert repo.find_open_duplicates("key") == [a.incident_id]
        statements = []
        repo.conn.set_trace_callback(statements.append)
        assert repo.list_active_incidents("payments-gateway") == [a]
        reads = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
        assert len(reads) == 1 and "INNER JOIN" in reads[0].upper()
        index = repo.conn.execute("PRAGMA index_info(idx_incidents_component_status)").fetchall()
        assert [r[2] for r in index] == ["component", "status"]
        assert repo.list_active_incidents("' OR 1=1 --") == []


def test_legacy_schema_migration(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE incidents (incident_id TEXT PRIMARY KEY, title TEXT NOT NULL, component TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, resolved_at TEXT)")
        conn.execute("INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?)",
                     ("OLD", "Legacy", "payments-gateway", "P0", "OPEN", REF, None))
    with SQLiteIncidentRepository(str(path)) as repo:
        assert repo.get_incident("OLD").title == "Legacy"
        assert repo.find_open_duplicates("key") == []


def test_default_memory_empty(monkeypatch, runner):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    result = runner.invoke(app, ["summary"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"total_active": 0, "breached_count": 0, "incidents": []}


def test_aware_default_reference(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "aware.db"))
    with repository_factory() as repo:
        repo.save_incident(make_incident("A", severity="P2", created="2026-01-01T09:00:00-05:00"))
    with TestClient(create_app()) as client:
        response = client.get(ENDPOINT)
    assert response.status_code == 200
    assert response.json()["total_active"] == 1
