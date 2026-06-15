"""Load fixed fixture data for Phase 1 theme research."""

import json
from pathlib import Path

from astra.theme_research.contracts import FixtureThemeDataset

LOW_ALTITUDE_ECONOMY_FIXTURE = "low_altitude_economy.json"
FIXTURE_DIR = Path(__file__).with_name("fixtures")


def load_low_altitude_economy_fixture() -> FixtureThemeDataset:
    """Load the fixed low-altitude economy fixture dataset."""
    fixture_path = FIXTURE_DIR / LOW_ALTITUDE_ECONOMY_FIXTURE
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return FixtureThemeDataset.model_validate(payload)
