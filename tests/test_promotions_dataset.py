from pathlib import Path

import pytest

from src.data.promotions import load_promotions, load_relegations

DATASET = Path(__file__).parents[1] / "data" / "promotions_brasileirao_2018_2026.json"


def test_versioned_promotion_dataset_is_complete() -> None:
    entries = load_promotions(DATASET)
    assert len(entries) == 36
    assert {entry.serie_a_season for entry in entries} == set(range(2018, 2027))
    assert [entry.team_id for entry in entries if entry.serie_a_season == 2026] == [
        "coritiba",
        "athletico",
        "chapecoense",
        "remo",
    ]


def test_promotion_dataset_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "promotions.json"
    path.write_text('{"schema_version":"promotions-brasileirao/v1","entries":[],"sources":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_promotions(path)


def test_versioned_relegation_dataset_is_complete() -> None:
    entries = load_relegations(DATASET)
    assert len(entries) == 36
    assert {entry.serie_a_season for entry in entries} == set(range(2017, 2026))
    assert {entry.team_id for entry in entries if entry.serie_a_season == 2025} == {
        "ceara",
        "fortaleza",
        "juventude",
        "sport",
    }
