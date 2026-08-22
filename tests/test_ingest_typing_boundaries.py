import pandas as pd

from src.ingest import normalize
from src.ingest_fbref import parse_player_stats


def test_normalize_keeps_dataframe_shape_and_nullable_scores():
    raw = pd.DataFrame(
        [
            {
                "date": "2026-08-22",
                "home_team": "Flamengo",
                "away_team": "Palmeiras",
                "home_score": "2",
                "away_score": "",
                "tournament": "Brasileirão Série A",
                "city": "Rio de Janeiro",
                "country": "Brazil",
                "neutral": "false",
            }
        ]
    )

    result = normalize(raw)

    assert isinstance(result, pd.DataFrame)
    assert result.iloc[0]["home_score"] == 2
    assert pd.isna(result.iloc[0]["away_score"])
    assert result.iloc[0]["neutral"] == 0


def test_parse_player_stats_preserves_fbref_numeric_semantics():
    html = """
    <table id="stats_standard_24">
      <thead><tr><th>Player</th><th>Squad</th><th>Pos</th><th>MP</th><th>Min</th>
      <th>Gls</th><th>Ast</th><th>xG</th><th>xAG</th></tr></thead>
      <tbody>
        <tr><td>Jogador A</td><td>Flamengo</td><td>FW</td><td>12</td><td>1,234</td>
        <td>5</td><td>3</td><td>4.7</td><td>--</td></tr>
      </tbody>
    </table>
    """

    rows = parse_player_stats(html, "Brasileirão Série A", "2026")

    assert rows == [("Jogador A", "Flamengo", "Brasileirão Série A", "2026", "FW", 1234, 12, 5, 3, 4.7, None)]
