"""Espelho sofascore_matches → matches (fundação do domínio Brasileirão).

No wc-predictor a tabela `matches` (Elo + calibração do Poisson) vinha do CSV
martj42 de SELEÇÕES — não existe equivalente público para clubes. Aqui a fonte
única é o Sofascore: depois de `python -m src.ingest_sofascore`, este script
espelha os jogos ENCERRADOS de sofascore_matches para `matches`, que alimenta
ratings.compute_ratings e model.fit_goal_model sem mudar uma linha do motor.

Regras:
- SÓ as competições listadas em cfg['sofascore']['competitions'] são espelhadas.
  Sem esse filtro o SELECT varria a tabela inteira e carimbava
  cfg['tournament_name'] em tudo: no dia que outra competição entrar na mesma
  base (o Roadmap SS7/RESEARCH-05 pede histórico de Série B pra prior de
  promovido), ela seria espelhada como se fosse Série A e envenenaria o treino
  em silêncio. Filtrar agora custa uma cláusula; descobrir depois custa uma
  temporada de resultado inválido;
- tournament = cfg['tournament_name'] (chave de k_factor, uma só por domínio);
- neutral = 0 (liga de pontos corridos: mando de campo real, sempre);
- upsert idempotente (PK date+home+away) — rodadas novas entram, nada duplica;
- fixtures futuros (home_score IS NULL no sofascore_matches) também entram,
  com placar NULL: é o que o simulador/predict --fixtures enxergam.

Uso: python scripts/sync_matches_from_sofascore.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import db  # noqa: E402
from src.ingest import ROOT, load_config  # noqa: E402
from src.obs import get_logger, setup_logging  # noqa: E402

log = get_logger()


def sync(conn, tournament: str, competitions: list[str]) -> tuple[int, int]:
    if not competitions:
        sys.exit("nenhuma competição em sofascore.competitions — nada a espelhar")
    placeholders = ",".join("?" for _ in competitions)
    rows = conn.execute(
        "SELECT date, home_team, away_team, home_score, away_score "
        "FROM sofascore_matches "
        "WHERE date IS NOT NULL AND home_team IS NOT NULL AND away_team IS NOT NULL "
        f"AND competition IN ({placeholders})",
        competitions,
    ).fetchall()
    out = [(d, h, a, hs, as_, tournament, "", "", 0) for d, h, a, hs, as_ in rows]
    if out:
        db.upsert_matches(conn, out)
    played = conn.execute("SELECT COUNT(*) FROM matches WHERE home_score IS NOT NULL").fetchone()[0]
    fixtures = conn.execute("SELECT COUNT(*) FROM matches WHERE home_score IS NULL").fetchone()[0]
    return played, fixtures


def main() -> None:
    setup_logging(ROOT / "data")
    cfg = load_config()
    tournament = cfg.get("tournament_name")
    if not tournament:
        sys.exit("config.yaml sem tournament_name — defina antes de espelhar")
    competitions = [c["name"] for c in (cfg.get("sofascore") or {}).get("competitions") or []]
    conn = db.connect(str(ROOT / cfg["database"]))
    played, fixtures = sync(conn, tournament, competitions)
    log.info(
        "matches espelhado do sofascore (%d competições): %d jogadas, %d fixtures",
        len(competitions),
        played,
        fixtures,
    )


if __name__ == "__main__":
    main()
