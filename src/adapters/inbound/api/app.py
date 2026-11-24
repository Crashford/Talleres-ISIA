"""Adaptador REST de IncidentOps."""

from dataclasses import asdict

from fastapi import FastAPI, HTTPException

from src.adapters.inbound.api.schemas import (
    TriageRequest, TriageResponse, ActiveIncidentsSummaryResponse,
)
from src.adapters.outbound.factory import repository_factory
from src.application.services import IncidentService, ValidationError


def create_app(repo_factory=repository_factory) -> FastAPI:
    app = FastAPI(title="IncidentOps")
    service = IncidentService(repo_factory)

    @app.post("/api/v1/incidents/triage", response_model=TriageResponse)
    def triage(request: TriageRequest) -> dict:
        try:
            result = service.triage_incident(request.incident_id, request.raw_text)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return asdict(result)

    @app.get("/api/v1/incidents/summary", response_model=ActiveIncidentsSummaryResponse)
    def summary(component: str | None = None, reference_time: str | None = None) -> dict:
        try:
            return asdict(service.get_active_incidents_summary(component, reference_time))
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return app


app = create_app()
