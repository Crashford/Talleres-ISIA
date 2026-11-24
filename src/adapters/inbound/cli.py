"""Adaptador CLI de IncidentOps."""

import json
from dataclasses import asdict

import typer

from src.application.services import IncidentService, ValidationError

app = typer.Typer()


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


if __name__ == "__main__":
    app()
