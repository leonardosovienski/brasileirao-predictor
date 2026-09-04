"""persist_h14_prospective — persistência append-only da coorte H14
(h14-serving-v2-vs-climatologia-prequential-prospectivo).

A trial FOI PRÉ-REGISTRADA em 2026-08-26 (`data/trials.json`), mas
`collection_status` continua "NOT_STARTED": o pré-registro só declara o
desenho, não persiste nada. `activation_condition` exige persistir os dois
braços — serving-v2 e climatologia prequential — append-only, ANTES do
kickoff, com fingerprint do código. É exatamente o que este script faz, e só
isso: NÃO calcula RPS, NÃO compara os braços, NÃO decide GO/NO-GO. Avaliação
só acontece em n>=900 (`min_n_avaliacao`), ponto único, sem olhadas
intermediárias — script separado, a ser escrito quando a coorte atingir esse
tamanho.

Braço A — serving-v2: usa o cache vivo do cron (`current_elo`,
`model_parameters`), igual ao padrão já usado por `emit_h9_shadow.py`. NÃO
refita nada aqui; lê o que `cron_update_models` já calculou.

Braço B — climatologia prequential: Dirichlet(1,1,1) sobre TODOS os jogos
already-completed em `matches` com kickoff estritamente anterior ao da
partida avaliada (mesmo `block_guard` declarado na trial: "kickoff estrito
no modelo; climatologia congelada por bloco de data" — aqui não há bloco de
data porque a persistência é por partida individual, não por corrida
walk-forward; a garantia equivalente é kickoff estritamente anterior).

Idempotente: cada `event_id` só entra uma vez no ledger
(data/research/h14_serving_vs_climatologia.jsonl); reexecuções não duplicam
nem reescrevem.

Uso (Task Scheduler, cadência sugerida: mesma do emit_h9_shadow, 15 min):
    python brasileirao_scripts/persist_h14_prospective.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry  # noqa: E402

from brasileirao_predictor import db, model  # noqa: E402
from brasileirao_predictor.ingest import load_config  # noqa: E402

TRIAL = "h14-serving-v2-vs-climatologia-prequential-prospectivo"
TRIALS_PATH = ROOT / "data" / "trials.json"
LEDGER_PATH = ROOT / "data" / "research" / "h14_serving_vs_climatologia.jsonl"

# Persiste só dentro de uma janela pré-kickoff — não expõe a previsão a mudar
# de Elo/params por dias antes do jogo, mas também não é uma decisão de
# execução (não há "melhor preço" a esperar, é só registro). 24h é
# consistente com a janela mais longa já usada no projeto para outras
# capturas pré-jogo (T-24h).
HORIZON = timedelta(hours=24)
MAX_MODEL_CACHE_AGE = timedelta(hours=12)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def trial_params(trials_path: Path = TRIALS_PATH) -> dict[str, Any]:
    trial = next((t for t in TrialRegistry(trials_path).load() if t["name"] == TRIAL), None)
    if trial is None:
        sys.exit(f"trial {TRIAL!r} não registrada — rode scripts/prereg_h14_serving_v2.py antes")
    return trial["params"]


def code_fingerprint(params: dict[str, Any], config_hash: str, home_advantage: float) -> str:
    """Muda se o desenho pré-registrado, o hash de config do serving ou o
    home_advantage mudarem — qualquer um desses invalidaria a comparabilidade
    das linhas já persistidas com as novas."""
    policy = {
        "trial": TRIAL,
        "algorithm_version": params["algorithm_version"],
        "ensemble_xg_enabled": params["ensemble_xg_enabled"],
        "retrain_every": params["retrain_every"],
        "elo_policy": "current_elo",
        "config_hash": config_hash,
        "home_advantage": home_advantage,
    }
    return hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()[:16]


def _in_window(kickoff_at: str, now: datetime) -> bool:
    try:
        kickoff = datetime.fromisoformat(str(kickoff_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if kickoff.tzinfo is None:
        return False
    return kickoff - HORIZON <= now < kickoff


def _require_fresh_model_cache(cached, now: datetime) -> None:
    if not cached or len(cached) < 7:
        raise RuntimeError("cache de modelo ausente — rode python -m brasileirao_predictor.cron_update_models")
    try:
        computed_at = datetime.fromisoformat(str(cached[6]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError("cache de modelo sem timestamp UTC válido") from exc
    if computed_at.tzinfo is None or computed_at.utcoffset() is None:
        raise RuntimeError("cache de modelo sem timestamp UTC válido")
    age = now.astimezone(UTC) - computed_at.astimezone(UTC)
    if age < timedelta(0) or age > MAX_MODEL_CACHE_AGE:
        raise RuntimeError(f"cache de modelo stale ({age}); rode python -m brasileirao_predictor.cron_update_models")


def _upcoming_fixtures(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT event_id, home_team, away_team, kickoff_at FROM sofascore_matches "
        "WHERE home_score IS NULL AND kickoff_at IS NOT NULL"
    ).fetchall()
    return [
        {"event_id": eid, "home_team": home, "away_team": away, "kickoff_at": kickoff_at}
        for eid, home, away, kickoff_at in rows
    ]


def _completed_matches_before(conn, kickoff_at: str) -> list[tuple[int, int]]:
    """Placares finais de jogos com kickoff estritamente anterior — a mesma
    query PIT usada por `completed_matches_with_kickoff`, mas restrita ao
    corte de UMA partida em vez de devolver tudo."""
    rows = db.completed_matches_with_kickoff(conn)
    out = []
    for _date, _home, _away, home_score, away_score, _tournament, _neutral, row_kickoff in rows:
        if row_kickoff is None or row_kickoff >= kickoff_at:
            continue
        out.append((int(home_score), int(away_score)))
    return out


def _outcome_1x2(home_goals: int, away_goals: int) -> int:
    """0=derrota do mandante, 1=empate, 2=vitória do mandante."""
    if home_goals > away_goals:
        return 2
    if home_goals == away_goals:
        return 1
    return 0


def _climatology_probs(prior_results: list[tuple[int, int]]) -> dict[str, float]:
    """Dirichlet(1,1,1) prequential: só usa resultados com kickoff
    estritamente anterior ao da partida avaliada."""
    counts = [1, 1, 1]
    for home_goals, away_goals in prior_results:
        counts[_outcome_1x2(home_goals, away_goals)] += 1
    total = sum(counts)
    return {
        "p_away": counts[0] / total,
        "p_draw": counts[1] / total,
        "p_home": counts[2] / total,
        "n_prior": len(prior_results),
    }


def run(
    *,
    now: datetime | None = None,
    trials_path: Path = TRIALS_PATH,
    ledger_path: Path = LEDGER_PATH,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    cfg = load_config()
    params = trial_params(trials_path)
    home_adv = float(cfg["elo"]["home_advantage"])

    conn = db.connect(str(db_path or (ROOT / cfg["database"])), read_only=True)
    try:
        cached_params = db.load_params(conn)
        _require_fresh_model_cache(cached_params, now)
        a, b, alpha, rho, _n_matches, config_hash, _computed_at = cached_params
        elo = db.load_elo(conn)
        fixtures = _upcoming_fixtures(conn)
        already = {row["event_id"] for row in _load_jsonl(ledger_path)}
        outcomes = []
        for fixture in fixtures:
            event_id = fixture["event_id"]
            if event_id in already or not _in_window(fixture["kickoff_at"], now):
                continue
            home, away = fixture["home_team"], fixture["away_team"]
            if home not in elo or away not in elo:
                outcomes.append({"event_id": event_id, "home": home, "away": away, "status": "MISSING_ELO_TEAM"})
                continue
            fingerprint = code_fingerprint(params, config_hash, home_adv)
            prediction = model.predict_match(elo[home], elo[away], (a, b, alpha, rho), home_adv)
            prior_results = _completed_matches_before(conn, fixture["kickoff_at"])
            climatology = _climatology_probs(prior_results)
            record = {
                "event_id": event_id,
                "home": home,
                "away": away,
                "kickoff_at": fixture["kickoff_at"],
                "predicted_at": now.isoformat(timespec="seconds"),
                "code_fingerprint": fingerprint,
                "serving_v2": {
                    "p_home": round(prediction["p_win"], 6),
                    "p_draw": round(prediction["p_draw"], 6),
                    "p_away": round(prediction["p_loss"], 6),
                    "elo_home": round(elo[home], 1),
                    "elo_away": round(elo[away], 1),
                },
                "climatology": {
                    "p_home": round(climatology["p_home"], 6),
                    "p_draw": round(climatology["p_draw"], 6),
                    "p_away": round(climatology["p_away"], 6),
                    "n_prior": climatology["n_prior"],
                },
            }
            _append_jsonl(ledger_path, record)
            already.add(event_id)
            outcomes.append({"event_id": event_id, "home": home, "away": away, "status": "PERSISTED"})
    finally:
        conn.close()
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args()
    outcomes = run()
    summary = {
        "trial": TRIAL,
        "evaluated": len(outcomes),
        "persisted": sum(1 for o in outcomes if o["status"] == "PERSISTED"),
        "outcomes": outcomes,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
