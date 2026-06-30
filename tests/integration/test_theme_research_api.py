from fastapi.testclient import TestClient

from astra.api.app import app


def test_theme_research_endpoint_returns_pool_and_report() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/theme-research",
        json={"theme": "低空经济", "market": "cn_a", "max_results": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_version"] == "phase1.v1"
    assert payload["request"]["normalized_query"] == "低空经济"
    assert len(payload["result"]["pool"]) == 3
    assert payload["result"]["report"]["not_investment_advice"]
    assert [stage["stage"] for stage in payload["result"]["pipeline"]] == [
        "candidate_recall",
        "evidence_enrichment",
        "coarse_rank",
        "deep_rank",
        "report_generation",
    ]


def test_theme_research_endpoint_can_omit_report() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/theme-research",
        json={"theme": "低空经济", "include_report": False, "max_results": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["result"]["pool"]) == 2
    assert payload["result"]["report"] is None
    assert [stage["stage"] for stage in payload["result"]["pipeline"]] == [
        "candidate_recall",
        "evidence_enrichment",
        "coarse_rank",
        "deep_rank",
    ]


def test_theme_research_endpoint_returns_no_candidates_error() -> None:
    client = TestClient(app)

    response = client.post("/api/theme-research", json={"theme": "完全不存在的主题"})

    assert response.status_code == 404
    payload = response.json()
    assert payload["contract_version"] == "phase1.v1"
    assert payload["error"]["code"] == "no_candidates"


def test_theme_research_endpoint_returns_invalid_request_error() -> None:
    client = TestClient(app)

    response = client.post("/api/theme-research", json={"theme": "   "})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_request"


def test_theme_research_endpoint_returns_unsupported_market_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/theme-research",
        json={"theme": "低空经济", "market": "us"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "unsupported_market"
