"""Adaptador CLI de IncidentOps."""

import json
from dataclasses import asdict
from datetime import datetime

import typer

from src.application.services import (
    IncidentNotFoundError,
    IncidentService,
    PersistentStorageUnavailableError,
    ValidationError,
)
from src.adapters.outbound.factory import repository_factory

app = typer.Typer()
APPLICATION_ERRORS = (ValidationError, IncidentNotFoundError, PersistentStorageUnavailableError)


def _json_payload(result) -> str:
    def encode(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [encode(item) for item in value]
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        return value

    return json.dumps(encode(asdict(result)), ensure_ascii=False)


@app.callback()
def main() -> None:
    """Herramientas de soporte IncidentOps."""


@app.command()
def triage(
    incident_id: str = typer.Option(...),
    raw_text: str = typer.Option(...),
) -> None:
    try:
        result = IncidentService().triage_incident(incident_id, raw_text)
    except ValidationError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(json.dumps(asdict(result), ensure_ascii=False))


@app.command()
def summary(
    component: str | None = typer.Option(None),
    reference_time: str | None = typer.Option(None),
) -> None:
    """Consultar incidentes activos y evaluación de SLA."""
    try:
        result = IncidentService(repository_factory).get_active_incidents_summary(component, reference_time)
    except ValidationError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(json.dumps(asdict(result), ensure_ascii=False))


@app.command()
def create(
    title: str = typer.Option(...),
    raw_text: str = typer.Option(...),
    incident_id: str | None = typer.Option(None),
    created_at: str | None = typer.Option(None),
    status: str | None = typer.Option(None),
) -> None:
    """Registrar un incidente con almacenamiento persistente."""
    try:
        result = IncidentService(repository_factory).create_incident(
            title, raw_text, incident_id, created_at, status
        )
    except APPLICATION_ERRORS as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(_json_payload(result))


@app.command()
def sla(
    incident_id: str = typer.Option(...),
    reference_time: str | None = typer.Option(None),
) -> None:
    """Auditar el SLA de un incidente registrado."""
    try:
        result = IncidentService(repository_factory).evaluate_incident_sla(incident_id, reference_time)
    except APPLICATION_ERRORS as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(_json_payload(result))


if __name__ == "__main__":
    app()
