"""Aceptación BDD del contrato H001 (E001–E005)."""

import json

import pytest

from src.adapters.inbound.cli import app

ENDPOINT = "/api/v1/incidents/triage"
PAYMENT = {"incident_id": "INC-1001", "raw_text": "HTTP 502 Bad Gateway en pasarela de pagos"}


def test_bdd_critical_payment_outage(client):
    # Given un reporte crítico de pagos.
    # When el frontend solicita triaje.
    response = client.post(ENDPOINT, json=PAYMENT)
    # Then obtiene todos los campos de clasificación.
    assert response.status_code == 200
    assert response.json() == {
        "incident_id": "INC-1001",
        "severity": "P0",
        "component": "payments-gateway",
        "rationale": "Fallo HTTP 502 en servicio crítico de pagos: P0 preventivo; alcance global por confirmar.",
        "consistency_ratio": 1.0,
        "recommended_team": "Backend-Core",
        "duplicate_group_key": "payments-gateway:http-502-outage",
    }


def test_bdd_individual_account_lockout(client):
    # Given una cuenta individual bloqueada con urgencia subjetiva.
    # When se solicita el triaje.
    response = client.post(ENDPOINT, json={
        "incident_id": "INC-1002", "raw_text": "URGENTE hoy: mi cuenta está bloqueada"
    })
    # Then no se eleva falsamente a P0.
    assert response.status_code == 200
    assert response.json()["severity"] == "P2"
    assert response.json()["recommended_team"] == "Security-IAM"


@pytest.mark.parametrize("payload", [
    {"incident_id": "", "raw_text": "reporte"},
    {"incident_id": "  ", "raw_text": "reporte"},
    {"incident_id": "INC", "raw_text": ""},
    {"incident_id": "INC", "raw_text": "  "},
    {"incident_id": "INC"},
    {"incident_id": 42, "raw_text": "reporte"},
    {"incident_id": "INC", "raw_text": None},
])
def test_bdd_empty_input_http(client, payload):
    # Given datos inválidos; When se solicita triaje; Then se rechazan.
    assert client.post(ENDPOINT, json=payload).status_code == 422


def test_bdd_cli_triage_parity(client, runner):
    # Given el mismo reporte; When se ejecuta el CLI.
    result = runner.invoke(app, [
        "triage", "--incident-id", PAYMENT["incident_id"],
        "--raw-text", PAYMENT["raw_text"],
    ])
    # Then la salida es equivalente a REST.
    assert result.exit_code == 0, result.output
    response = client.post(ENDPOINT, json=PAYMENT)
    assert response.status_code == 200
    assert json.loads(result.stdout) == response.json()


@pytest.mark.parametrize("incident_id,raw_text", [
    ("", "reporte"), ("  ", "reporte"), ("INC", ""), ("INC", "  "),
])
def test_bdd_empty_input_cli(runner, incident_id, raw_text):
    # Given datos vacíos; When se ejecuta CLI; Then código 1 y sin JSON.
    result = runner.invoke(app, [
        "triage", "--incident-id", incident_id, "--raw-text", raw_text,
    ])
    assert result.exit_code == 1
    assert not result.stdout.strip()
    assert "vacío" in result.stderr
