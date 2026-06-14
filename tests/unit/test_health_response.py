from astra.api.app import HealthResponse


def test_health_response_defaults() -> None:
    response = HealthResponse()

    assert response.model_dump() == {
        "status": "ok",
        "service": "astra",
    }

