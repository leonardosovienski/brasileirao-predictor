"""Gera data/teams_brasileirao.json — os 20 clubes da Série A 2026 (PASSO 2.2).

Fonte: o próprio cache da coleta do Sofascore (data/sofascore_cache/
unique-tournament_325_season_<id>_events_last_*.json) — os payloads de events
carregam homeTeam/awayTeam com id, name e slug. Nada é digitado à mão: se o
clube não apareceu num jogo coletado da temporada 2026, ele não entra.

Estrutura de saída:
  {"season": "2026", "source": "sofascore ut_id=325 season_id=87678",
   "teams": {"Flamengo": {"sofascore_id": 5981, "slug": "flamengo"}, ...}}

Uso: python scripts/gen_teams_json.py   (após python -m src.ingest_sofascore)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ingest import load_config          # noqa: E402

OUT = ROOT / "data" / "teams_brasileirao.json"


def main() -> None:
    cfg = load_config()
    scfg = cfg["sofascore"]
    cache = ROOT / scfg["cache_dir"]
    comp = next((c for c in scfg["competitions"] if str(c["season"]) == "2026"), None)
    if not comp:
        sys.exit("config sem a temporada 2026 em sofascore.competitions")

    teams: dict[str, dict] = {}
    pattern = f"unique-tournament_{comp['ut_id']}_season_{comp['season_id']}_events_last_*.json"
    files = sorted(cache.glob(pattern))
    if not files:
        sys.exit(f"cache vazio ({pattern}) — rode python -m src.ingest_sofascore antes")
    for f in files:
        for ev in json.loads(f.read_text(encoding="utf-8")).get("events", []):
            for side in ("homeTeam", "awayTeam"):
                t = ev.get(side) or {}
                name, tid = t.get("name"), t.get("id")
                if name and tid:
                    teams[name] = {"sofascore_id": tid, "slug": t.get("slug", "")}

    out = {"season": "2026",
           "source": f"sofascore ut_id={comp['ut_id']} season_id={comp['season_id']}",
           "n_teams": len(teams),
           "teams": dict(sorted(teams.items()))}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"{OUT.name}: {len(teams)} clubes")
    if len(teams) != 20:
        print(f"AVISO: esperava 20 clubes na Série A, achei {len(teams)} — "
              "temporada 2026 incompleta no cache?")
    for name, info in sorted(teams.items()):
        print(f"  {name:<28} id={info['sofascore_id']}")


if __name__ == "__main__":
    main()
