from astra.theme_research import load_low_altitude_economy_fixture


def test_low_altitude_economy_fixture_loads_stable_dataset() -> None:
    dataset = load_low_altitude_economy_fixture()

    assert dataset.fixture_id == "low_altitude_economy"
    assert dataset.display_name == "低空经济"
    assert dataset.market == "cn_a"
    assert dataset.as_of == "2026-06-15"
    assert len(dataset.companies) >= 6


def test_low_altitude_economy_fixture_contains_expected_aliases() -> None:
    dataset = load_low_altitude_economy_fixture()

    assert {"低空经济", "低空", "eVTOL", "无人机"}.issubset(set(dataset.aliases))


def test_low_altitude_economy_fixture_company_records_are_complete() -> None:
    dataset = load_low_altitude_economy_fixture()

    for company in dataset.companies:
        assert company.symbol
        assert company.name
        assert company.concepts
        assert company.recall_keywords
        assert len(company.evidence) >= 3
        assert len(company.risks) >= 1


def test_low_altitude_economy_fixture_covers_relevance_edges() -> None:
    dataset = load_low_altitude_economy_fixture()

    high_relevance = [
        company
        for company in dataset.companies
        if "低空经济" in company.concepts and "低空经济" in company.recall_keywords
    ]
    weak_relevance = [
        company for company in dataset.companies if "低空经济" not in company.concepts
    ]
    low_confidence_evidence = [
        evidence
        for company in dataset.companies
        for evidence in company.evidence
        if evidence.confidence == "low"
    ]

    assert len(high_relevance) >= 3
    assert len(weak_relevance) >= 1
    assert low_confidence_evidence


def test_low_altitude_economy_fixture_records_data_boundary() -> None:
    dataset = load_low_altitude_economy_fixture()
    boundary_text = "\n".join(dataset.data_boundary)

    assert "固定样例数据" in boundary_text
    assert "不代表实时市场事实" in boundary_text
    assert "不是投资建议" in boundary_text
