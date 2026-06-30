"""FastAPI application entrypoint."""

from collections.abc import Mapping
from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from astra.theme_research import (
    ThemeResearchError,
    ThemeResearchErrorResponse,
    ThemeResearchRequest,
    ThemeResearchResponse,
    ThemeResearchServiceError,
    run_theme_research,
)


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

    @app.post(
        "/api/theme-research",
        response_model=ThemeResearchResponse,
        responses={
            400: {"model": ThemeResearchErrorResponse},
            404: {"model": ThemeResearchErrorResponse},
            500: {"model": ThemeResearchErrorResponse},
        },
    )
    def theme_research(payload: object = Body(...)) -> ThemeResearchResponse | JSONResponse:
        try:
            request = _theme_research_request_from_payload(payload)
            return run_theme_research(request)
        except ThemeResearchServiceError as exc:
            return _theme_research_error_response(exc)

    return app


app = create_app()


def _theme_research_request_from_payload(payload: object) -> ThemeResearchRequest:
    if not isinstance(payload, Mapping):
        raise ThemeResearchServiceError(
            "invalid_request",
            "请求体必须是 JSON object。",
        )

    payload_dict = dict(payload)
    market = payload_dict.get("market", "cn_a")
    if market != "cn_a":
        raise ThemeResearchServiceError(
            "unsupported_market",
            "Phase 1 仅支持 cn_a 市场。",
            {"market": market},
        )

    try:
        return ThemeResearchRequest.model_validate(payload_dict)
    except ValidationError as exc:
        raise ThemeResearchServiceError(
            "invalid_request",
            "主题研究请求参数无效。",
            {"errors": _jsonable_validation_errors(exc)},
        ) from exc


def _theme_research_error_response(error: ThemeResearchServiceError) -> JSONResponse:
    status_code = {
        "invalid_request": 400,
        "unsupported_market": 400,
        "no_candidates": 404,
        "internal_error": 500,
    }[error.code]
    response = ThemeResearchErrorResponse(
        error=ThemeResearchError(
            code=error.code,
            message=error.message,
            details=error.details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


def _jsonable_validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for error in exc.errors():
        errors.append(
            {
                key: value
                for key, value in error.items()
                if key != "ctx"
            }
        )
    return errors
