"""Adaptador REST de IncidentOps."""

from dataclasses import asdict

from fastapi import FastAPI, HTTPException

from src.adapters.inbound.api.schemas import TriageRequest, TriageResponse
from src.application.services import IncidentService, ValidationError


def create_app() -> FastAPI:
    app = FastAPI(title="IncidentOps")
    service = IncidentService()

    @app.post("/api/v1/incidents/triage", response_model=TriageResponse)
    def triage(request: TriageRequest) -> dict:
        try:
            result = service.triage_incident(request.incident_id, request.raw_text)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return asdict(result)

    return app


app = create_app()
