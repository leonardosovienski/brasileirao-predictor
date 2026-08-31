"""permutation_test — controle NEGATIVO do pipeline sobre dados REAIS.

`predictor_core.testing.harness.attest_pipeline_power` já faz o controle
POSITIVO: prova que a régua detecta sinal sintético. Faltava o lado oposto, e é
o que pega bug que nenhum teste unitário pega — a régua REJEITA ruído quando
roda sobre a SUA base, o SEU carregamento, a SUA ordenação?

COMO FUNCIONA
-------------
Embaralha os RESULTADOS entre as partidas e roda o mesmo walk-forward. O
embaralhamento destrói a associação time↔desfecho, mas preserva as marginais
da liga (quantos jogos terminam em vitória do mandante, empate, fora) porque
cada `result` viaja inteiro, com home_goals e away_goals na ordem original.

Isso deixa exatamente UM sinal de pé: as marginais globais. E as marginais
globais são precisamente o que a climatologia captura. Logo:

    skill score vs climatologia, sobre dados embaralhados  ->  ~ZERO

Se o modelo AINDA bater a climatologia com IC95 acima de zero em dados sem
sinal, não existe modelo bom: existe VAZAMENTO em algum ponto do pipeline.

POR QUE ISSO VALE O TEMPO DE CPU
--------------------------------
Todos os vazamentos encontrados na auditoria de 2026-08-21 teriam aparecido
aqui: guarda de bloco ausente no Dixon-Coles e no Elo, ordenação por
data-sem-hora dentro da rodada, xG do jogo previsto no nível errado do dict.
Nenhum deles quebrava teste unitário — todos inflavam a métrica em silêncio.

LEITURA DO VEREDITO
-------------------
* PASSOU  — nenhuma permutação teve IC95 do ganho estritamente acima de zero.
  O pipeline rejeita ruído: o skill medido nos dados reais é atribuível a
  sinal, não a vazamento.
* FALHOU  — pelo menos uma permutação "bateu" a climatologia com significância.
  Trate como BUG até provar o contrário. Nenhum resultado do painel é confiável
  enquanto isso não for explicado.

Uso:
    python brasileirao_scripts/permutation_test.py --period 2021-01-01,2024-12-31
    python brasileirao_scripts/permutation_test.py --permutations 5 --engine serving

CUSTO: cada permutação roda um walk-forward completo. Com a cadência padrão
(`--retrain-every 100`) isso é da ordem do baseline; com cadência de rodada é
uma ordem de grandeza pior. Comece pequeno.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.measurement.metrics import rps  # noqa: E402

from brasileirao_scripts.benchmark_predictor import (  # noqa: E402
    DEFAULT_ENGINE,
    ENGINES,
    MIN_HISTORY,
    RETRAIN_EVERY,
    _climatology_probs,
    _half_life_for,
    _load_observations,
    _run_walkforward,
    _skill_score_ci,
)
from brasileirao_predictor.ingest import load_config  # noqa: E402

log = logging.getLogger("permutation_test")

MODEL_TAG = "H4_DIXON_COLES_CALIBRATED"
DEFAULT_PERIOD = "2021-01-01,2024-12-31"
SEALED_HOLDOUT_YEAR = "2025"
DEFAULT_PERMUTATIONS = 3
BASE_SEED = 20260821


def _permute(observations: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    """Embaralha os `result` ENTRE as partidas, mantendo a ordem temporal das
    partidas intacta.

    Cada `result` viaja INTEIRO — home_goals e away_goals continuam juntos e na
    mesma ordem. Isso preserva as marginais da liga (e com elas a climatologia)
    e destrói só o que interessa: a associação entre quem jogou e o que
    aconteceu. Embaralhar os gols separadamente também mataria a correlação
    entre placares, mudando a distribuição que a climatologia enxerga, e o
    controle deixaria de ser comparável."""
    resultados = [o["result"] for o in observations]
    random.Random(seed).shuffle(resultados)
    return [dict(o, result=r) for o, r in zip(observations, resultados)]


def _skill_vs_climatology(rows: list[dict[str, Any]]) -> dict[str, Any]:
    probs = [[r["p_loss"], r["p_draw"], r["p_win"]] for r in rows]
    outcomes = [r["actual_1x2"] for r in rows]
    baseline = _climatology_probs(rows)
    perdas_modelo = [rps([p], [y]) for p, y in zip(probs, outcomes)]
    perdas_base = [rps([p], [y]) for p, y in zip(baseline, outcomes)]
    ci = _skill_score_ci(perdas_modelo, perdas_base)
    rps_modelo, rps_base = rps(probs, outcomes), rps(baseline, outcomes)
    return {
        "n": len(rows),
        "rps": round(rps_modelo, 6),
        "rps_climatology": round(rps_base, 6),
        "skill_score": round(1 - (rps_modelo / rps_base), 6) if rps_base else None,
        # Ganho médio por jogo (climatologia - modelo): positivo = modelo melhor.
        "gain_ci95": [round(ci[0], 6), round(ci[1], 6)] if ci else None,
        "beats_climatology": bool(ci and ci[0] is not None and ci[0] > 0),
    }


def _corrida(
    observations: list[dict[str, Any]],
    half_life: float,
    retrain_every: int,
    start: str,
    end: str,
    engine: str,
    cfg: dict[str, Any] | None,
    rotulo: str,
) -> dict[str, Any]:
    def _progress(feitas: int, total: int) -> None:
        log.info("  %s: %d/%d previsões", rotulo, feitas, total)

    rows, _ev = _run_walkforward(observations, half_life, retrain_every, progress=_progress, engine=engine, cfg=cfg)
    rows = [r for r in rows if (not start or r["date"] >= start) and (not end or r["date"] <= end)]
    if not rows:
        raise SystemExit(f"nenhuma previsão em [{start or '-inf'}, {end or '+inf'}]")
    return _skill_vs_climatology(rows)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--period", default=DEFAULT_PERIOD)
    p.add_argument("--permutations", type=int, default=DEFAULT_PERMUTATIONS)
    p.add_argument("--retrain-every", type=int, default=RETRAIN_EVERY)
    p.add_argument("--engine", default=DEFAULT_ENGINE, choices=list(ENGINES))
    p.add_argument("--output", type=Path, default=None)
    p.add_argument(
        "--unseal-holdout",
        action="store_true",
        help="permite alcançar 2025. NÃO usar: gastar o holdout num controle negativo o queima igual.",
    )
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    start, _, end = args.period.partition(",")
    start, end = start.strip(), end.strip()
    if not args.unseal_holdout and (not end or end >= f"{SEALED_HOLDOUT_YEAR}-01-01"):
        log.error(
            "--period termina em %s, dentro/além do holdout selado de %s. Um controle negativo "
            "consome o holdout tanto quanto um experimento (Regra 7).",
            end or "(aberto)",
            SEALED_HOLDOUT_YEAR,
        )
        return 1
    if args.permutations < 1:
        p.error("--permutations >= 1")

    cfg = load_config()
    half_life = _half_life_for(MODEL_TAG)
    observations = _load_observations(end)
    if len(observations) < MIN_HISTORY + 50:
        log.error("histórico insuficiente (%d) para min_history=%d", len(observations), MIN_HISTORY)
        return 1

    log.info("corrida de REFERÊNCIA (dados reais, sem embaralhar)")
    real = _corrida(observations, half_life, args.retrain_every, start, end, args.engine, cfg, "real")
    log.info(
        "  real: skill=%.6f IC95=%s bate_climatologia=%s",
        real["skill_score"],
        real["gain_ci95"],
        real["beats_climatology"],
    )

    permutadas = []
    for i in range(args.permutations):
        seed = BASE_SEED + i
        log.info("permutação %d/%d (seed=%d)", i + 1, args.permutations, seed)
        r = _corrida(
            _permute(observations, seed),
            half_life,
            args.retrain_every,
            start,
            end,
            args.engine,
            cfg,
            f"perm{i + 1}",
        )
        r["seed"] = seed
        log.info(
            "  perm%d: skill=%.6f IC95=%s bate=%s",
            i + 1,
            r["skill_score"],
            r["gain_ci95"],
            r["beats_climatology"],
        )
        permutadas.append(r)

    vazando = [r for r in permutadas if r["beats_climatology"]]
    passou = not vazando
    detalhe = (
        "nenhuma permutação bateu a climatologia com significância — o pipeline rejeita ruído"
        if passou
        else (
            f"{len(vazando)} de {len(permutadas)} permutações 'bateram' a climatologia em dados SEM SINAL "
            "— trate como VAZAMENTO até provar o contrário; nenhum resultado do painel é confiável até isso "
            "ser explicado"
        )
    )
    log.info("VEREDITO: %s (%s)", "PASSOU" if passou else "FALHOU", detalhe)

    relatorio = {
        "schema_version": "permutation-test/1",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "engine": args.engine,
        "period": [start or None, end or None],
        "retrain_every": args.retrain_every,
        "half_life_days": half_life,
        "reference_run": real,
        "permutations": permutadas,
        "verdict": {"passed": passou, "detail": detalhe},
    }
    out = args.output or ROOT / "reports" / f"permutation_test_{args.engine}_{date.today().isoformat()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    log.info("relatório: %s", out)
    return 0 if passou else 2


if __name__ == "__main__":
    sys.exit(main())
