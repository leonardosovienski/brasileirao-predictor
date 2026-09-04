"""persist_h15_prospective — persistência append-only da coorte H15
(h15-refit10-vs-100-serving-v2-prospectivo).

A trial FOI PRÉ-REGISTRADA em 2026-08-26 (`data/trials.json`), mas
`collection_status` continua "NOT_STARTED": o pré-registro só declara o
desenho. `activation_condition` exige persistir os dois braços — refit a
cada 10 jogos (treatment) e a cada 100 jogos (control) — append-only, ANTES
do kickoff, com fingerprint do código. É exatamente o que este script faz, e
só isso: NÃO calcula RPS, NÃO compara os braços, NÃO decide GO/NO-GO.
Avaliação só acontece em n>=900 (`min_n_avaliacao`), ponto único, sem
olhadas intermediárias — script separado, a ser escrito quando a coorte
atingir esse tamanho.

DIFERENÇA PARA H14
-------------------
H14 lê o cache VIVO do cron (`current_elo`/`model_parameters`) — um único
braço de serving comparado à climatologia. H15 precisa manter DOIS estados
de modelo independentes, cada um refitado na SUA PRÓPRIA cadência (10 vs.
100 jogos concluídos desde o último refit) — não pode usar o cache de
produção, que é refitado a cada ingestão. Por isso cada braço tem seu
próprio arquivo de estado (`data/research/h15_state_<braço>.json`) com o
Elo e os parâmetros congelados no último refit, e o script refita chamando
`cron_update_models.compute` (a MESMA função que o cron de produção usa)
sobre `matches` — sempre só com jogos já concluídos, então um refit nunca
pode enxergar o resultado de uma partida ainda não apitada: o corte
"kickoff estrito" é estrutural (compute() só vê home_score IS NOT NULL) e
não depende de nenhum filtro adicional aqui.

Idempotente: cada `event_id` só entra uma vez no ledger
(data/research/h15_refit10_vs_100.jsonl); reexecuções não duplicam.

Uso (Task Scheduler, cadência sugerida: mesma do H14/H9, 15 min):
    python brasileirao_scripts/persist_h15_prospective.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry  # noqa: E402

from brasileirao_predictor import cron_update_models, db, model  # noqa: E402
from brasileirao_predictor.ingest import load_config  # noqa: E402

TRIAL = "h15-refit10-vs-100-serving-v2-prospectivo"
TRIALS_PATH = ROOT / "data" / "trials.json"
LEDGER_PATH = ROOT / "data" / "research" / "h15_refit10_vs_100.jsonl"
STATE_DIR = ROOT / "data" / "research"

# Mesma janela pré-kickoff usada por persist_h14_prospective.py: registro,
# não decisão de execução, 24h é consistente com a captura pré-jogo mais
# longa já usada no projeto.
HORIZON = timedelta(hours=24)


@dataclass(frozen=True)
class Arm:
    name: str
    retrain_every: int

    @property
    def state_path(self) -> Path:
        return STATE_DIR / f"h15_state_{self.name}.json"


ARMS = (Arm("treatment_refit10", 10), Arm("control_refit100", 100))


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
        sys.exit(f"trial {TRIAL!r} não registrada — rode scripts/prereg_h15_refit_cadence.py antes")
    return trial["params"]


def design_fingerprint(arm: Arm, params: dict[str, Any], config_hash_value: str, home_advantage: float) -> str:
    """Identidade do DESENHO do braço — não muda a cada refit (isso seria
    esperado, é a mesma comparação continuando); muda só se o código, a
    config do serving ou o home_advantage mudarem, invalidando a
    comparabilidade das linhas já persistidas com as novas."""
    policy = {
        "trial": TRIAL,
        "arm": arm.name,
        "retrain_every": arm.retrain_every,
        "algorithm_version": params["algorithm_version"],
        "config_hash": config_hash_value,
        "home_advantage": home_advantage,
    }
    return hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()[:16]


def _load_state(arm: Arm) -> dict[str, Any] | None:
    if not arm.state_path.exists():
        return None
    return json.loads(arm.state_path.read_text(encoding="utf-8"))


def _save_state(arm: Arm, state: dict[str, Any]) -> None:
    arm.state_path.parent.mkdir(parents=True, exist_ok=True)
    arm.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _refit(cfg: dict[str, Any], conn, now: datetime) -> dict[str, Any] | None:
    """Roda a MESMA função que o cron de produção usa (`cron_update_models.compute`)
    sobre o snapshot atual de `matches` — só jogos já concluídos entram, por
    construção da própria função (não filtra nada extra aqui)."""
    result = cron_update_models.compute(cfg, conn)
    if result is None:
        return None
    elo, params, n_matches = result
    return {
        "elo": dict(elo),
        "params": list(params),
        "n_matches_at_refit": n_matches,
        "refit_at": now.isoformat(timespec="seconds"),
    }


def _ensure_fresh_state(arm: Arm, cfg: dict[str, Any], conn, n_completed_now: int, now: datetime) -> dict[str, Any]:
    state = _load_state(arm)
    due = state is None or (n_completed_now - state["n_matches_at_refit"]) >= arm.retrain_every
    if due:
        refit = _refit(cfg, conn, now)
        if refit is None:
            if state is None:
                raise RuntimeError(f"braço {arm.name}: sem histórico suficiente para o primeiro refit")
            return state  # sem jogos concluídos novos o bastante para refitar — mantém o que já havia
        _save_state(arm, refit)
        return refit
    return state


def _upcoming_fixtures(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT event_id, home_team, away_team, kickoff_at FROM sofascore_matches "
        "WHERE home_score IS NULL AND kickoff_at IS NOT NULL"
    ).fetchall()
    return [
        {"event_id": eid, "home_team": home, "away_team": away, "kickoff_at": kickoff_at}
        for eid, home, away, kickoff_at in rows
    ]


def _in_window(kickoff_at: str, now: datetime) -> bool:
    try:
        kickoff = datetime.fromisoformat(str(kickoff_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if kickoff.tzinfo is None:
        return False
    return kickoff - HORIZON <= now < kickoff


def _predict_with_state(state: dict[str, Any], home: str, away: str, home_adv: float) -> dict[str, Any] | None:
    elo = state["elo"]
    if home not in elo or away not in elo:
        return None
    pred = model.predict_match(elo[home], elo[away], tuple(state["params"]), home_adv)
    return {
        "p_home": round(pred["p_win"], 6),
        "p_draw": round(pred["p_draw"], 6),
        "p_away": round(pred["p_loss"], 6),
        "elo_home": round(elo[home], 1),
        "elo_away": round(elo[away], 1),
        "n_matches_at_refit": state["n_matches_at_refit"],
        "refit_at": state["refit_at"],
    }


def run(
    *,
    now: datetime | None = None,
    trials_path: Path = TRIALS_PATH,
    ledger_path: Path = LEDGER_PATH,
    arms: tuple[Arm, ...] = ARMS,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    cfg = load_config()
    params = trial_params(trials_path)
    home_adv = float(cfg["elo"]["home_advantage"])

    conn = db.connect(str(db_path or (ROOT / cfg["database"])), read_only=True)
    try:
        n_completed_now = conn.execute("SELECT COUNT(*) FROM matches WHERE home_score IS NOT NULL").fetchone()[0]
        states = {arm.name: _ensure_fresh_state(arm, cfg, conn, n_completed_now, now) for arm in arms}
        config_hash_value = cron_update_models.config_hash(cfg)
        fingerprints = {arm.name: design_fingerprint(arm, params, config_hash_value, home_adv) for arm in arms}
        fixtures = _upcoming_fixtures(conn)
        already = {row["event_id"] for row in _load_jsonl(ledger_path)}
        outcomes = []
        for fixture in fixtures:
            event_id = fixture["event_id"]
            if event_id in already or not _in_window(fixture["kickoff_at"], now):
                continue
            home, away = fixture["home_team"], fixture["away_team"]
            arm_predictions = {}
            missing_elo = False
            for arm in arms:
                prediction = _predict_with_state(states[arm.name], home, away, home_adv)
                if prediction is None:
                    missing_elo = True
                    break
                arm_predictions[arm.name] = {**prediction, "code_fingerprint": fingerprints[arm.name]}
            if missing_elo:
                outcomes.append({"event_id": event_id, "home": home, "away": away, "status": "MISSING_ELO_TEAM"})
                continue
            record = {
                "event_id": event_id,
                "home": home,
                "away": away,
                "kickoff_at": fixture["kickoff_at"],
                "predicted_at": now.isoformat(timespec="seconds"),
                **arm_predictions,
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
