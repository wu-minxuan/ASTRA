"""FastAPI application entrypoint."""

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response payload."""

    status: str = "ok"
    service: str = "astra"


def create_app() -> FastAPI:
    """Create the ASTRA API application."""
    app = FastAPI(title="ASTRA API")

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    return app


app = create_app()

