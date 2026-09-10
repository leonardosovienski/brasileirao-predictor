import json

import pytest

from brasileirao_predictor.data.promotions import load_promotions, load_relegations


def dataset():
    return {
        "schema_version": "promotions-brasileirao/v1",
        "sources": [{"serie_b_season": 2019, "url": "https://www.cbf.com.br/synthetic/b"}],
        "relegation_sources": [{"serie_a_season": 2019, "url": "https://www.cbf.com.br/synthetic/a"}],
        "entries": [
            dict(serie_a_season=2020, serie_b_season=2019, position=i, team_id=f"up-{i}", team_name=f"Synthetic {i}")
            for i in range(1, 5)
        ],
        "relegations": [
            dict(serie_a_season=2019, position=i, team_id=f"down-{i}", team_name=f"Synthetic {i}")
            for i in range(17, 21)
        ],
    }


@pytest.mark.parametrize("field,loader", [("entries", load_promotions), ("relegations", load_relegations)])
@pytest.mark.parametrize("defect", ["extra_position", "fractional_position", "duplicate_team", "invalid_identity"])
def test_invalid_season_roster_is_not_accepted_as_complete(tmp_path, field, loader, defect):
    value = dataset()
    rows = value[field]
    if defect == "extra_position":
        rows.append({**rows[0], "team_id": "unexpected-fifth-team"})
    elif defect == "fractional_position":
        rows[0]["position"] += 0.5
    elif defect == "duplicate_team":
        rows[1]["team_id"] = rows[0]["team_id"]
    else:
        rows[0]["team_id"] = None
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError):
        loader(path)


def test_valid_four_club_rosters_preserve_their_identity_and_order(tmp_path):
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(dataset()), encoding="utf-8")
    assert [row.team_id for row in load_promotions(path)] == [f"up-{i}" for i in range(1, 5)]
    assert [row.team_id for row in load_relegations(path)] == [f"down-{i}" for i in range(17, 21)]
