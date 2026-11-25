"""Fixtures de aceptación aisladas."""

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.adapters.inbound.api.app import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_url(tmp_path, monkeypatch):
    url = "sqlite:///" + str(tmp_path / "incidents.db")
    monkeypatch.setenv("DATABASE_URL", url)
    return url


@pytest.fixture
def api_client(db_url):
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def cli_runner():
    return CliRunner()
