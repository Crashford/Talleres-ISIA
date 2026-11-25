"""Adaptador REST de IncidentOps."""

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.adapters.inbound.api.schemas import (
    HealthResponse, TriageRequest, TriageResponse, ActiveIncidentsSummaryResponse,
    CreateIncidentRequest, IncidentCreatedResponse, SLAEvaluationResponse,
)
from src.adapters.outbound.factory import repository_factory
from src.application.services import (
    IncidentNotFoundError,
    IncidentService,
    PersistentStorageUnavailableError,
    ValidationError,
)


def create_app(repo_factory=repository_factory) -> FastAPI:
    app = FastAPI(title="IncidentOps")
    service = IncidentService(repo_factory)

    @app.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
    def health() -> dict | JSONResponse:
        if service.check_health():
            return {"status": "ok", "database": "connected"}
        return JSONResponse(status_code=503, content={"status": "error", "database": "unavailable"})

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

    @app.post("/api/v1/incidents", response_model=IncidentCreatedResponse, status_code=201)
    def create_incident(request: CreateIncidentRequest) -> dict:
        try:
            result = service.create_incident(
                request.title, request.raw_text, request.incident_id,
                request.created_at, request.status,
            )
        except PersistentStorageUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return asdict(result)

    @app.get("/api/v1/incidents/{incident_id}/sla", response_model=SLAEvaluationResponse)
    def sla(incident_id: str, reference_time: str | None = None) -> dict:
        try:
            return asdict(service.evaluate_incident_sla(incident_id, reference_time))
        except IncidentNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return app


app = create_app()
