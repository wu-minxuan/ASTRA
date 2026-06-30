from fastapi.testclient import TestClient

from astra.api.app import create_app
from astra.theme_research import (
    FixtureMarketDataProvider,
    ThemeResearchRequest,
    ThemeResearchResponse,
    ThemeResearchServiceError,
    load_low_altitude_economy_fixture,
    run_theme_research,
)


def make_test_client() -> TestClient:
    dataset = load_low_altitude_economy_fixture()
    provider = FixtureMarketDataProvider(dataset)

    def runner(request: ThemeResearchRequest) -> ThemeResearchResponse:
        return run_theme_research(request, market_data_provider=provider)

    return TestClient(create_app(research_runner=runner))


def test_theme_research_endpoint_returns_pool_and_report() -> None:
    client = make_test_client()

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
    client = make_test_client()

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
    client = make_test_client()

    response = client.post("/api/theme-research", json={"theme": "完全不存在的主题"})

    assert response.status_code == 404
    payload = response.json()
    assert payload["contract_version"] == "phase1.v1"
    assert payload["error"]["code"] == "no_candidates"


def test_theme_research_endpoint_returns_invalid_request_error() -> None:
    client = make_test_client()

    response = client.post("/api/theme-research", json={"theme": "   "})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_request"


def test_theme_research_endpoint_returns_unsupported_market_error() -> None:
    client = make_test_client()

    response = client.post(
        "/api/theme-research",
        json={"theme": "低空经济", "market": "us"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "unsupported_market"


def test_theme_research_endpoint_returns_provider_unavailable_error() -> None:
    def runner(request: ThemeResearchRequest) -> ThemeResearchResponse:
        raise ThemeResearchServiceError(
            "provider_unavailable",
            "AKShare 候选召回接口不可用。",
            {
                "provider": "akshare",
                "stage": "candidate_recall",
                "error_message": "AKShare call failed: stock_board_concept_name_em",
            },
        )

    client = TestClient(create_app(research_runner=runner))

    response = client.post("/api/theme-research", json={"theme": "低空经济"})

    assert response.status_code == 502
    payload = response.json()
    assert payload["contract_version"] == "phase1.v1"
    assert payload["error"]["code"] == "provider_unavailable"
    assert payload["error"]["details"]["provider"] == "akshare"
