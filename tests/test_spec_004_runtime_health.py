"""Aceptación H004: health y runtime en contenedores (E001–E006)."""

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from typer.testing import CliRunner

from src.adapters.inbound import cli as cli_module
from src.adapters.inbound.api.app import create_app
from src.adapters.outbound.factory import create_repository, repository_factory
from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.ports import IncidentRepositoryPort
from src.domain.models import Incident

SUCCESS_BODY = {"status": "ok", "database": "connected"}
ERROR_BODY = {"status": "error", "database": "unavailable"}


class HealthRepository:
    def __init__(self, healthy: bool) -> None:
        self.healthy = healthy

    def save_incident(self, incident: Incident) -> bool:
        return False

    def supports_persistent_writes(self) -> bool:
        return True

    def get_incident(self, incident_id: str) -> Incident | None:
        return None

    def find_open_duplicates(self, duplicate_group_key: str, incident_id: str) -> list[str]:
        return []

    def list_active_incidents(self, component_filter: str | None = None) -> list[Incident]:
        return []

    def check_health(self) -> bool:
        return self.healthy


def factory_for(repo: IncidentRepositoryPort):
    @contextmanager
    def _factory():
        yield repo

    return _factory


class FakeConnection:
    def __init__(self, row_shape: str = "dict") -> None:
        self.closed = False
        self.statements: list[tuple[str, tuple | None]] = []
        self.rowcount = 0
        self.commits = 0
        self.rollbacks = 0
        self.context_entries = 0
        self._row_shape = row_shape
        self._rows: list[dict | tuple] = []

    def execute(self, sql: str, params: tuple | None = None) -> "FakeConnection":
        self.statements.append((sql, params))
        normalized = " ".join(sql.split()).upper()
        if normalized.startswith("SELECT 1"):
            self._rows = [(1,)] if self._row_shape == "tuple" else [{"ping": 1}]
        else:
            self._rows = []
        self.rowcount = 1 if normalized.startswith("INSERT INTO INCIDENTS") else 0
        return self

    def fetchone(self) -> dict | tuple | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[dict | tuple]:
        return list(self._rows)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def __enter__(self) -> "FakeConnection":
        self.context_entries += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False

    def close(self) -> None:
        self.closed = True


def test_bdd_e001_health_connected(monkeypatch) -> None:
    repo = HealthRepository(True)
    assert isinstance(repo, IncidentRepositoryPort)
    monkeypatch.setattr(cli_module, "repository_factory", factory_for(repo))

    with TestClient(create_app(repo_factory=factory_for(repo))) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == SUCCESS_BODY

    result = CliRunner().invoke(cli_module.app, ["health"])
    assert result.exit_code == 0
    assert json_loads(result.stdout) == SUCCESS_BODY


def test_bdd_e002_health_unavailable(monkeypatch) -> None:
    repo = HealthRepository(False)
    monkeypatch.setattr(cli_module, "repository_factory", factory_for(repo))

    with TestClient(create_app(repo_factory=factory_for(repo))) as client:
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == ERROR_BODY

    result = CliRunner().invoke(cli_module.app, ["health"])
    assert result.exit_code == 1
    assert json_loads(result.stdout) == ERROR_BODY


def test_bdd_e003_default_sqlite_memory(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with repository_factory() as repo:
        assert isinstance(repo, SQLiteIncidentRepository)
        assert repo._persistent is False
        assert repo.check_health() is True


def test_bdd_e004_sqlite_url(tmp_path, monkeypatch) -> None:
    url = "sqlite:///" + str(tmp_path / "health.db")
    monkeypatch.setenv("DATABASE_URL", url)

    with repository_factory() as repo:
        assert isinstance(repo, SQLiteIncidentRepository)
        assert repo.supports_persistent_writes() is True
        assert repo.check_health() is True


def test_bdd_e005_postgres_url(monkeypatch) -> None:
    connection = FakeConnection()
    observed: dict = {}

    def fake_connect(dsn: str, row_factory=None) -> FakeConnection:
        observed["dsn"] = dsn
        observed["row_factory"] = row_factory
        return connection

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    url = "postgresql://user:pass@db:5432/incidentops"

    with repository_factory(url) as repo:
        assert repo.supports_persistent_writes() is True
        assert repo.check_health() is True
        incident = Incident(
            "INC-H004-001", "Fallo en pasarela", "payments-gateway", "P0", "OPEN",
            datetime(2026, 11, 24, 10, 0), None, "Backend-Core", "dup-key",
        )
        assert repo.save_incident(incident) is True

    assert observed["dsn"] == url
    assert observed["row_factory"] is dict_row
    assert any(sql.strip().upper().startswith("SELECT 1") for sql, _ in connection.statements)
    inserts = [(sql, params) for sql, params in connection.statements
               if sql.lstrip().upper().startswith("INSERT INTO INCIDENTS")]
    assert inserts
    insert_sql, insert_params = inserts[-1]
    assert insert_sql.count("%s") == 9
    assert "ON CONFLICT (INCIDENT_ID) DO NOTHING" in insert_sql.upper()
    assert insert_params[5] == incident.created_at.isoformat()
    assert insert_params[6] is None


def test_regression_health_select_one_tuple_and_factory_alias(monkeypatch) -> None:
    assert create_repository is repository_factory

    connection = FakeConnection(row_shape="tuple")

    def fake_connect(dsn: str, row_factory=None) -> FakeConnection:
        return connection

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    url = "postgresql://user:pass@db:5432/incidentops"

    with create_repository(url) as repo:
        assert repo.check_health() is True

    assert any(sql.strip().upper().startswith("SELECT 1") for sql, _ in connection.statements)


def test_regression_connection_lifecycle_stays_open_until_repository_exit(monkeypatch) -> None:
    connection = FakeConnection()

    def fake_connect(dsn: str, row_factory=None) -> FakeConnection:
        return connection

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    url = "postgresql://user:pass@db:5432/incidentops"
    incident = Incident(
        "INC-H004-LIFECYCLE", "Fallo en pasarela", "payments-gateway", "P0", "OPEN",
        datetime(2026, 11, 24, 10, 0), None, "Backend-Core", "dup-key",
    )

    with create_repository(url) as repo:
        assert repo.check_health() is True
        assert repo.save_incident(incident) is True
        assert repo.get_incident(incident.incident_id) is None
        assert repo.find_open_duplicates("dup-key", incident.incident_id) == []
        assert repo.list_active_incidents() == []
        assert repo._conn is connection
        assert connection.closed is False
        assert connection.context_entries == 0
        assert connection.commits >= 2
        assert connection.rollbacks == 0

    assert connection.closed is True


def test_bdd_e006_compose_structure() -> None:
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (root / ".dockerignore").read_text(encoding="utf-8")
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "python:3.12-slim" in dockerfile
    assert "uv" in dockerfile.lower()
    for pattern in (".git/", ".venv/", "__pycache__/", ".pytest_cache/", ".ruff_cache/", "evidence/"):
        assert pattern in dockerignore
    assert "postgres:16-alpine" in compose
    assert "volumes:" in compose
    assert "pg_isready" in compose
    assert "service_healthy" in compose
    assert "/health" in compose
    assert "urllib.request" in compose


def json_loads(value: str) -> dict:
    import json

    return json.loads(value)
