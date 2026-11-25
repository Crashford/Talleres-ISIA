"""Aceptación H003: ciclo de vida, duplicados y SLA (E001–E015)."""

import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.adapters.inbound.cli import app as cli_app
from src.adapters.outbound.factory import repository_factory
from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.services import IncidentService
from src.domain import sla_calculator
from src.domain.models import Incident


def test_temporal_default_created_at_is_local_aware():
    created = sla_calculator.resolve_created_at(None)
    assert isinstance(created, datetime)
    assert created.tzinfo is not None and created.utcoffset() is not None


def test_temporal_explicit_created_at_is_respected():
    assert sla_calculator.resolve_created_at("2026-11-06T17:00:00") == datetime(2026, 11, 6, 17)


def test_temporal_omitted_reference_follows_stored_convention():
    naive = sla_calculator.resolve_reference_time(datetime(2026, 11, 6, 17))
    assert naive.tzinfo is None
    aware = sla_calculator.resolve_reference_time(
        datetime(2026, 11, 6, 17, tzinfo=timezone(timedelta(hours=-5))), severity="P2"
    )
    assert aware.utcoffset() == timedelta(hours=-5)


@pytest.mark.parametrize(
    ("created", "reference"),
    [
        ("2026-11-06T17:00:00", "2026-11-09T09:00:00Z"),
        ("2026-11-06T17:00:00Z", "2026-11-09T09:00:00"),
    ],
)
def test_temporal_rejects_naive_aware_mix(created, reference):
    with pytest.raises(ValueError):
        sla_calculator.resolve_reference_time(
            sla_calculator.parse_iso_datetime(created), reference, severity="P0"
        )


def test_temporal_rejects_distinct_offsets_in_business_hours():
    created = sla_calculator.parse_iso_datetime("2026-11-06T17:00:00-05:00")
    with pytest.raises(ValueError):
        sla_calculator.resolve_reference_time(created, "2026-11-09T09:00:00+00:00", severity="P2")


@pytest.mark.parametrize("reference", ["2026-11-06T16:59:59", "no-es-una-fecha", "2026-11-06"])
def test_temporal_rejects_invalid_or_earlier_reference(reference):
    with pytest.raises(ValueError):
        sla_calculator.resolve_reference_time(datetime(2026, 11, 6, 17), reference, severity="P0")


def test_temporal_resolved_range_keeps_breach_without_escalation():
    created = datetime(2026, 11, 6, 9)
    resolved_at = datetime(2026, 11, 6, 11)
    incident = Incident("INC-RESOLVED", "Resuelto", "payments-gateway", "P0", "RESOLVED", created, resolved_at)
    reference = sla_calculator.resolve_reference_time(created, "2026-11-06T12:00:00", incident.severity)
    evaluation = sla_calculator.evaluate_sla_status(incident, reference)
    assert evaluation.elapsed_minutes == 120
    assert not evaluation.requires_escalation


def _port_incident(ident, title, status="OPEN", key="key"):
    return Incident(
        ident, title, "payments-gateway", "P0", status,
        datetime(2026, 11, 9, 8), None, "Backend-Core", key,
    )


def test_port_atomic_insert_concurrent(tmp_path):
    path = str(tmp_path / "concurrent.db")
    original = _port_incident("INC-RACE", "Registro original")
    challenger = _port_incident("INC-RACE", "Intento sobrescritura")

    def save(incident):
        with SQLiteIncidentRepository(path) as repo:
            return repo.save_incident(incident)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, [original, challenger]))
    assert sorted(results) == [False, True]
    with SQLiteIncidentRepository(path) as repo:
        assert repo.get_incident("INC-RACE").title in {"Registro original", "Intento sobrescritura"}
        assert repo.get_incident("INC-RACE").incident_id == "INC-RACE"


def test_port_migration_and_duplicate_index(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE incidents (incident_id TEXT PRIMARY KEY, title TEXT NOT NULL, "
            "component TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL, "
            "created_at TEXT NOT NULL, resolved_at TEXT)"
        )
        conn.execute(
            "INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("OLD", "Legacy", "payments-gateway", "P0", "OPEN", "2026-11-09T08:00:00", None),
        )
    with SQLiteIncidentRepository(str(path)) as repo:
        columns = {row["name"] for row in repo.conn.execute("PRAGMA table_info(incidents)")}
        assert {"recommended_team", "duplicate_group_key"} <= columns
        index = repo.conn.execute("PRAGMA index_info(idx_incidents_dup_key)").fetchall()
        assert [row[2] for row in index] == ["duplicate_group_key", "status"]
        assert repo.get_incident("OLD").recommended_team is None


def test_port_hydrates_classification_fields(tmp_path):
    with SQLiteIncidentRepository(str(tmp_path / "hydrate.db")) as repo:
        incident = _port_incident("INC-H", "Clasificado")
        assert repo.save_incident(incident) is True
        hydrated = repo.get_incident("INC-H")
        assert hydrated == incident
        assert hydrated.recommended_team == "Backend-Core"
        assert hydrated.duplicate_group_key == "key"


def test_port_duplicate_filter_includes_escalation(tmp_path):
    with SQLiteIncidentRepository(str(tmp_path / "dupes.db")) as repo:
        for ident, status in [
            ("INC-A", "OPEN"), ("INC-B", "IN_PROGRESS"),
            ("INC-C", "ESCALATION_REQUIRED"), ("INC-D", "RESOLVED"), ("INC-SELF", "OPEN"),
        ]:
            assert repo.save_incident(_port_incident(ident, ident, status)) is True
        assert repo.find_open_duplicates("key", "INC-SELF") == ["INC-A", "INC-B", "INC-C"]


def test_factory_keeps_ephemeral_default(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with repository_factory() as repo:
        assert repo.supports_persistent_writes() is False
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "file.db"))
    with repository_factory() as repo:
        assert repo.supports_persistent_writes() is True


P0_BODY = {
    "title": "HTTP 502 en pasarela de pagos",
    "raw_text": "HTTP 502 Bad Gateway en pasarela de pagos",
}
P2_BODY = {
    "title": "Latencia alta en API pública",
    "raw_text": "El dashboard tarda 12 segundos con 10.000 registros",
    "incident_id": "INC-P2F4E6A8",
    "created_at": "2026-11-06T17:00:00",
}


def _cli_create(runner, **overrides):
    payload = {**P0_BODY, **overrides}
    args = ["create", "--title", payload["title"], "--raw-text", payload["raw_text"]]
    for option, key in [("--incident-id", "incident_id"), ("--created-at", "created_at"), ("--status", "status")]:
        if key in payload:
            args += [option, str(payload[key])]
    return runner.invoke(cli_app, args)


def test_bdd_e001_create_valid(api_client, cli_runner, db_url, monkeypatch):
    response = api_client.post("/api/v1/incidents", json=P0_BODY)
    assert response.status_code == 201
    data = response.json()
    assert re.fullmatch(r"INC-[0-9A-F]{8}", data["incident_id"])
    assert data["status"] == "OPEN" and data["resolved_at"] is None
    assert data["severity"] == "P0" and data["component"] == "payments-gateway"
    assert data["recommended_team"] == "Backend-Core"
    assert data["is_duplicate"] is False and data["duplicate_of"] == []
    assert datetime.fromisoformat(data["created_at"]).utcoffset() is not None
    assert "raw_text" not in data

    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(Path(db_url.removeprefix("sqlite:///")).parent / "cli.db"))
    result = _cli_create(cli_runner)
    assert result.exit_code == 0, result.stderr
    cli_data = json.loads(result.stdout)
    assert re.fullmatch(r"INC-[0-9A-F]{8}", cli_data["incident_id"])
    assert cli_data["severity"] == data["severity"]
    assert cli_data["is_duplicate"] is False and cli_data["duplicate_of"] == []
    assert "raw_text" not in cli_data


@pytest.mark.parametrize("blank", [{"title": "   "}, {"raw_text": "   "}, {"title": ""}, {"raw_text": ""}])
def test_bdd_e002_blank_input(api_client, cli_runner, blank):
    response = api_client.post("/api/v1/incidents", json={**P0_BODY, **blank})
    assert response.status_code == 422
    result = _cli_create(cli_runner, **blank)
    assert result.exit_code == 1
    assert not result.stdout.strip()


def test_bdd_e011_duplicate_id(api_client, cli_runner, db_url):
    body = {**P0_BODY, "incident_id": "INC-DUP"}
    assert api_client.post("/api/v1/incidents", json=body).status_code == 201
    assert api_client.post("/api/v1/incidents", json=body).status_code == 422
    assert _cli_create(cli_runner, **body).exit_code == 1
    with repository_factory() as repo:
        assert repo.get_incident("INC-DUP").title == body["title"]

    def attempt(title):
        try:
            IncidentService(repository_factory).create_incident(
                title, body["raw_text"], "INC-RACE-API", "2026-11-09T08:00:00", "OPEN"
            )
            return "ok"
        except Exception:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ["Concurrente uno", "Concurrente dos"]))
    assert sorted(outcomes) == ["ok", "rejected"]
    with repository_factory() as repo:
        assert repo.get_incident("INC-RACE-API").title in {"Concurrente uno", "Concurrente dos"}
        assert repo.get_incident("INC-DUP").title == body["title"]


@pytest.mark.parametrize("status", ["RESOLVED", "UNKNOWN"])
def test_bdd_e013_invalid_initial_status(api_client, cli_runner, status):
    response = api_client.post("/api/v1/incidents", json={**P0_BODY, "status": status})
    assert response.status_code == 422
    result = _cli_create(cli_runner, status=status)
    assert result.exit_code == 1
    assert not result.stdout.strip()


def test_bdd_e014_create_parity(api_client, cli_runner, db_url, monkeypatch):
    rest = api_client.post("/api/v1/incidents", json=P2_BODY)
    assert rest.status_code == 201
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(Path(db_url.removeprefix("sqlite:///")).parent / "parity.db"))
    result = _cli_create(cli_runner, **P2_BODY)
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout) == rest.json()


def test_bdd_e015_ephemeral_storage(api_client, cli_runner, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    response = api_client.post("/api/v1/incidents", json=P0_BODY)
    assert response.status_code == 503
    result = _cli_create(cli_runner)
    assert result.exit_code == 1
    assert not result.stdout.strip()


@pytest.mark.parametrize("status", ["OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED"])
def test_bdd_e003_open_duplicate(api_client, status):
    first = api_client.post(
        "/api/v1/incidents", json={**P0_BODY, "incident_id": "INC-FIRST", "status": status}
    )
    assert first.status_code == 201
    second = api_client.post(
        "/api/v1/incidents", json={**P0_BODY, "incident_id": "INC-SECOND", "title": "Otro reporte 502"}
    )
    assert second.status_code == 201
    data = second.json()
    assert data["is_duplicate"] is True
    assert data["duplicate_of"] == ["INC-FIRST"]


def test_bdd_e004_no_duplicate(api_client):
    with repository_factory() as repo:
        resolved = Incident(
            "INC-OLD", "Anterior", "payments-gateway", "P0", "RESOLVED",
            datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 9), None,
            "payments-gateway:http-502-outage",
        )
        repo.save_incident(resolved)
    response = api_client.post("/api/v1/incidents", json={**P0_BODY, "incident_id": "INC-NEW"})
    assert response.status_code == 201
    assert response.json()["is_duplicate"] is False
    assert response.json()["duplicate_of"] == []
    other = api_client.post(
        "/api/v1/incidents",
        json={**P2_BODY, "incident_id": "INC-UNRELATED"},
    )
    assert other.json()["is_duplicate"] is False


SLA_EXPECTED = {
    "incident_id": "INC-P2F4E6A8",
    "reference_time": "2026-11-09T09:00:00",
    "elapsed_minutes": 120,
    "allowed_minutes": 480,
    "remaining_minutes": 360,
    "is_breached": False,
    "requires_escalation": False,
}


def _cli_sla(runner, incident_id, reference_time=None):
    args = ["sla", "--incident-id", incident_id]
    if reference_time is not None:
        args += ["--reference-time", reference_time]
    return runner.invoke(cli_app, args)


def _seed_p2(api_client):
    created = api_client.post("/api/v1/incidents", json=P2_BODY)
    assert created.status_code == 201
    assert created.json()["severity"] == "P2"


def test_bdd_e005_sla_audit(api_client, cli_runner):
    _seed_p2(api_client)
    response = api_client.get(
        "/api/v1/incidents/INC-P2F4E6A8/sla",
        params={"reference_time": "2026-11-09T09:00:00"},
    )
    assert response.status_code == 200
    assert response.json() == SLA_EXPECTED
    result = _cli_sla(cli_runner, "INC-P2F4E6A8", "2026-11-09T09:00:00")
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout) == SLA_EXPECTED


def test_bdd_e006_deterministic_p2(api_client):
    _seed_p2(api_client)
    response = api_client.get(
        "/api/v1/incidents/INC-P2F4E6A8/sla",
        params={"reference_time": "2026-11-09T09:00:00"},
    )
    assert response.json() == SLA_EXPECTED


def test_bdd_e007_resolved_sla(api_client):
    with repository_factory() as repo:
        repo.save_incident(Incident(
            "INC-RESOLVED-SLA", "Resuelto", "payments-gateway", "P0", "RESOLVED",
            datetime(2026, 11, 6, 17), datetime(2026, 11, 20, 9),
        ))
    response = api_client.get(
        "/api/v1/incidents/INC-RESOLVED-SLA/sla",
        params={"reference_time": "2026-11-21T09:00:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reference_time"] == "2026-11-21T09:00:00"
    assert data["elapsed_minutes"] > data["allowed_minutes"]
    assert data["is_breached"] is True
    assert data["requires_escalation"] is False


def test_bdd_e008_rest_cli_sla_parity(api_client, cli_runner):
    _seed_p2(api_client)
    response = api_client.get(
        "/api/v1/incidents/INC-P2F4E6A8/sla",
        params={"reference_time": "2026-11-09T09:00:00"},
    )
    result = _cli_sla(cli_runner, "INC-P2F4E6A8", "2026-11-09T09:00:00")
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout) == response.json()


def test_bdd_e009_missing_incident(api_client, cli_runner):
    assert api_client.get("/api/v1/incidents/INC-NO-EXISTE/sla").status_code == 404
    result = _cli_sla(cli_runner, "INC-NO-EXISTE", "2026-11-09T09:00:00")
    assert result.exit_code == 1
    assert not result.stdout.strip()


@pytest.mark.parametrize("reference", ["no-valido", "2026-11-06T16:00:00"])
def test_bdd_e010_invalid_reference(api_client, cli_runner, reference):
    _seed_p2(api_client)
    response = api_client.get(
        "/api/v1/incidents/INC-P2F4E6A8/sla", params={"reference_time": reference}
    )
    assert response.status_code == 422
    result = _cli_sla(cli_runner, "INC-P2F4E6A8", reference)
    assert result.exit_code == 1
    assert not result.stdout.strip()


def test_bdd_e012_incompatible_dates(api_client):
    _seed_p2(api_client)
    for reference in ["2026-11-09T09:00:00Z", "2026-11-09T09:00:00+00:00"]:
        response = api_client.get(
            "/api/v1/incidents/INC-P2F4E6A8/sla", params={"reference_time": reference}
        )
        assert response.status_code == 422

    with repository_factory() as repo:
        repo.save_incident(Incident(
            "INC-AWARE", "Aware", "payments-gateway", "P2", "OPEN",
            datetime(2026, 11, 6, 17, tzinfo=timezone(timedelta(hours=-5))),
        ))
    assert api_client.get(
        "/api/v1/incidents/INC-AWARE/sla", params={"reference_time": "2026-11-09T09:00:00"}
    ).status_code == 422
    assert api_client.get(
        "/api/v1/incidents/INC-AWARE/sla", params={"reference_time": "2026-11-09T09:00:00+00:00"}
    ).status_code == 422
    assert api_client.get("/api/v1/incidents/INC-AWARE/sla").status_code == 200
