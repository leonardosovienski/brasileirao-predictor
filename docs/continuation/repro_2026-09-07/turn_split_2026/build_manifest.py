"""Map official CBF rounds to local identities using metadata, never outcomes."""
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
SOURCE_URL = "https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_BA_sica_Brasileiro_SA_rie_A_2026_d64996b4d8.pdf"
ALIASES = {"Atlético": "Atlético Mineiro"}
OFFICIAL_RESOLUTIONS = {
    202: {"event_id": 16987855, "excluded_local_ids": [15235419],
          "kickoff_at": "2026-09-16T22:30:00+00:00",
          "source": "https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-a/2026/botafogo-x-gremio/832091?view=escalacao",
          "reason": "Official CBF fixture202/round21 rescheduled to16Sep19:30Brasilia; select unique local identity matching that kickoff, retain old ID as alias only."}
}
TEAMS = ["Fluminense", "Grêmio", "Botafogo", "Cruzeiro", "São Paulo", "Flamengo", "Corinthians", "Bahia", "Mirassol", "Vasco da Gama", "Atlético", "Palmeiras", "Internacional", "Athletico", "Coritiba", "Red Bull Bragantino", "Vitória", "Remo", "Chapecoense", "Santos"]
TEAM_PATTERN = "(?:" + "|".join(re.escape(name) for name in sorted(TEAMS, key=len, reverse=True)) + ")"
PAIR = re.compile(r"(" + TEAM_PATTERN + r")\s+([A-Z]{2})\s+x\s+(" + TEAM_PATTERN + r")\s+([A-Z]{2})$")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    rows = []
    visible_round = None
    for line in (ROOT / "cbf_tabela_basica_2026.txt").read_text(encoding="utf-8").splitlines():
        lead = re.match(r"^(\d{3})\s+(\d{1,2})(ª)?\s+(.+)$", line)
        if not lead:
            continue
        pair = PAIR.search(lead[4])
        if not pair:
            raise ValueError("Unparsed fixture row: " + line)
        # Only visible ordinal round headers are authoritative. The PDF contains
        # invisible template numbers in merged cells (e.g. ref330 has hidden34).
        if lead[3] == "ª":
            visible_round = int(lead[2])
        ref, rnd = int(lead[1]), visible_round
        assert rnd == (ref - 1) // 10 + 1, (ref, rnd, line)
        rows.append({"cbf_ref": ref, "season": 2026, "round": rnd,
                     "role": "test_exploratory" if rnd <= 19 else "paper_betting",
                     "home_cbf": pair[1], "away_cbf": pair[3],
                     "home_team": ALIASES.get(pair[1], pair[1]), "away_team": ALIASES.get(pair[3], pair[3]),
                     "source": SOURCE_URL})
    assert len(rows) == 380
    assert sorted(r["cbf_ref"] for r in rows) == list(range(1, 381))
    assert Counter(r["round"] for r in rows) == Counter({r: 10 for r in range(1, 39)})
    by_pair = {(row["home_team"], row["away_team"]): row for row in rows}
    assert len(by_pair) == 380
    for pair, row in by_pair.items():
        assert abs(by_pair[pair[::-1]]["round"] - row["round"]) == 19
    home_counts = Counter(row["home_team"] for row in rows)
    away_counts = Counter(row["away_team"] for row in rows)
    assert len(home_counts) == 20 and all(home_counts[t] == away_counts[t] == 19 for t in home_counts)
    with sqlite3.connect((REPO / "data/matches.db").as_uri() + "?mode=ro", uri=True) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.row_factory = sqlite3.Row
        query = """SELECT event_id,competition,season,date,kickoff_at,home_team,away_team,superseded_by_event_id
                   FROM sofascore_matches WHERE date>='2026-01-01' AND date<'2027-01-01' ORDER BY date,event_id"""
        metadata = [dict(row) for row in conn.execute(query).fetchall()]
        historical_counts = [dict(row) for row in conn.execute("""SELECT substr(date,1,4) AS year,COUNT(*) AS rows
            FROM sofascore_matches WHERE date>='2021-01-01' AND date<'2026-01-01' GROUP BY substr(date,1,4) ORDER BY year""").fetchall()]
    save("local_2026_metadata.json", metadata)
    save("historical_metadata_counts.json", historical_counts)
    candidates = defaultdict(list)
    unmatched = []
    for row in metadata:
        pair = (row["home_team"], row["away_team"])
        if pair not in by_pair:
            unmatched.append(row)
        else:
            candidates[pair].append(row)
    issues = []
    for row in rows:
        versions = candidates[(row["home_team"], row["away_team"])]
        current = [r for r in versions if r["superseded_by_event_id"] is None]
        resolution = OFFICIAL_RESOLUTIONS.get(row["cbf_ref"])
        if resolution and len(current) > 1:
            chosen = [r for r in current if r["event_id"] == resolution["event_id"] and r["kickoff_at"] == resolution["kickoff_at"]]
            assert len(chosen) == 1
            assert set(r["event_id"] for r in current) - {resolution["event_id"]} == set(resolution["excluded_local_ids"])
            current = chosen
            row["identity_resolution"] = resolution
        row["local_event_ids"] = [r["event_id"] for r in versions]
        row["superseded_event_ids"] = [r["event_id"] for r in versions if r["superseded_by_event_id"] is not None]
        row["identity_status"] = "MATCHED" if len(current) == 1 else "AMBIGUOUS" if len(current) > 1 else "NOT_IN_LOCAL_CATALOG"
        row["event_id"] = current[0]["event_id"] if len(current) == 1 else None
        row["kickoff_at"] = current[0]["kickoff_at"] if len(current) == 1 else None
        if row["identity_status"] != "MATCHED":
            issues.append({"cbf_ref": row["cbf_ref"], "home":row["home_team"], "away":row["away_team"], "versions":versions})
    save("schedule_manifest.json", rows)
    save("mapping_issues.json", {"unmatched_local":unmatched, "official_rows_with_issue":issues})
    print(json.dumps({"official_fixtures":len(rows), "roles":dict(Counter(r['role'] for r in rows)),
                      "local_metadata_rows":len(metadata), "identities":dict(Counter(r['identity_status'] for r in rows)),
                      "superseded_local_rows":sum(r['superseded_by_event_id'] is not None for r in metadata),
                      "unmatched_local":len(unmatched), "issues":issues[:8]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
