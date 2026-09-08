import json
import sqlite3
from pathlib import Path

repo = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
names = [
    "benchmark_serving_v2_corrected_2021_2024_2026-08-26.json",
    "losses_serving_v2_2021_2024.json",
    "benchmark_serving_v2_corrected_2025_diagnostic_2026-08-26.json",
    "benchmark_serving_market_no_vig_2026-08-22.json",
]
for name in names:
    obj = json.loads((repo / "reports" / name).read_text(encoding="utf-8"))
    print(name)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, dict):
                print(key, "dict", list(value.keys())[:25])
            elif isinstance(value, list):
                print(key, "list", len(value), "first_item_keys", list(value[0])[:25] if value and isinstance(value[0], dict) else None)
            else:
                print(key, value)
    else:
        print(type(obj).__name__, len(obj), list(obj[0]) if obj and isinstance(obj[0], dict) else None)

conn = sqlite3.connect((repo / "data" / "matches.db").as_uri() + "?mode=ro", uri=True)
conn.execute("PRAGMA query_only=ON")
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT substr(date,1,4) AS year,
           COUNT(*) AS fixtures,
           SUM(home_score IS NOT NULL AND away_score IS NOT NULL) AS completed,
           SUM(kickoff_at IS NOT NULL) AS kickoff_present,
           SUM(odds_home IS NOT NULL AND odds_draw IS NOT NULL AND odds_away IS NOT NULL) AS odds_1x2_complete,
           SUM(odds_home_open IS NOT NULL AND odds_draw_open IS NOT NULL AND odds_away_open IS NOT NULL) AS opening_1x2_complete,
           SUM(odds_over IS NOT NULL AND odds_under IS NOT NULL) AS odds_ou_complete,
           SUM(home_xg IS NOT NULL AND away_xg IS NOT NULL) AS xg_pair_present
    FROM sofascore_matches
    WHERE date >= '2021-01-01' AND date < '2026-01-01'
    GROUP BY substr(date,1,4) ORDER BY year
""").fetchall()
print("HISTORICAL_COVERAGE", json.dumps([dict(row) for row in rows], ensure_ascii=False))
conn.close()
