"""PRÉ-REGISTRO — pilha de serving vs. climatologia, coorte PROSPECTIVA.

Este script NÃO MEDE NADA. Ele congela um desenho experimental e sai. Medir
aqui destruiria a única coisa que ele produz: uma hipótese declarada antes de
os dados existirem.

POR QUE PROSPECTIVO, E NÃO 2021-2024 NEM 2025
---------------------------------------------
Em 2026-08-22 mediu-se que a pilha de serving (ensemble de xG desligado) bate a
climatologia em 2021-2024: RPS 0,213339 vs 0,219989, IC95 do delta
[-0,010544, -0,002858], com o controle negativo passando no mesmo motor.

Esse resultado é forte, mas **não é confirmatório**, e não há pré-registro que
o conserte:

* **2021-2024 já foi visto.** Registrar agora a mesma medição na mesma amostra
  seria pré-registro só no nome — o efeito escolheu a hipótese, não o
  contrário. É o que a Regra 10 impede.
* **2025 é holdout selado (Regra 7)** e a arquitetura NÃO está congelada: a
  TRACK A (01B, 02, 02B, 03, 04, 05, 06, 07, 08+) não começou. Gastar o holdout
  agora o queimaria antes da decisão para a qual ele foi reservado.
* **2026 é exploratório (Regra 1)** — não valida arquitetura.

Sobra uma única amostra genuinamente cega: **as partidas que ainda não foram
jogadas**. É a Regra 8 do próprio Roadmap ("2027+ confirmação prospectiva") e
a única forma honesta de confirmar o achado de 2026-08-22.

PODER — POR QUE n >= 900, E POR QUE NÃO ESPIAR ANTES
-----------------------------------------------------
Do resultado de 2021-2024: n=1318, delta=-0,006650, meia-largura do IC95
0,003843, logo SE ≈ 0,001961.

    n para o IC excluir zero com o MESMO efeito (poder ~50%):  440
    n para poder ~80%:                                          899
    → 899 / 380 jogos por temporada ≈ 2,4 temporadas

Avaliar antes de n=900 é **subpoderado por construção**: com n=440 a chance de
o IC excluir zero é ~50% mesmo que o efeito seja exatamente o observado, e um
"inconclusiva" ali não informa nada. Por isso o desenho declara **um único
ponto de avaliação**, sem olhadas intermediárias — olhar e parar quando dá
significativo é o mecanismo clássico de inflar falso-positivo, e o registro
existe justamente para tornar isso impossível de esconder.

GATE DECLARADO ANTES DOS DADOS
-------------------------------
COMPROVADA exige, na coorte prospectiva, TODAS as condições:

  1. RPS: IC95 do delta vs. climatologia **inteiramente abaixo de zero**;
  2. nenhum guardrail (log-loss, Brier 1X2, Brier OU2.5) materialmente pior —
     isto é, IC95 inteiro do lado ruim (guardrail que dispara com ruído vira
     veto arbitrário);
  3. controle negativo do motor `serving` passando na MESMA coorte.

Qualquer outro resultado é REFUTADA ou INCONCLUSIVA. Não há caminho em que se
reescreva o critério depois de ver o número.

NÃO AUTORIZA CAPITAL. É hipótese de qualidade de modelo (RPS), não de mercado —
bater a climatologia não é bater o preço de casa. O gate econômico é outro,
separado (Regra 8 do Roadmap), e depende do `market_no_vig`, que não existe.

Uso:
    python brasileirao_scripts/prereg_serving_vs_climatologia.py            # registra e sai
    python brasileirao_scripts/prereg_serving_vs_climatologia.py --dry-run  # só imprime
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry  # noqa: E402

from brasileirao_scripts.benchmark_predictor import MIN_HISTORY, RETRAIN_EVERY  # noqa: E402
from brasileirao_scripts.research_01a_refit_cadence import (  # noqa: E402
    BLOCK_LENGTH,
    GUARDRAIL_METRICS,
    N_BOOT,
    SEED,
    attest_rps_power,
)

log = logging.getLogger("prereg_serving")

TRIALS = ROOT / "data" / "trials.json"
TRIAL_NAME = "h13-serving-vs-climatologia-prospectivo"
MODEL_TAG = "H4_DIXON_COLES_CALIBRATED"
ENGINE = "serving"
BASELINE = "climatology"

# Ponto ÚNICO de avaliação. Ver o bloco PODER no docstring: 440 dá poder ~50%,
# 899 dá ~80% para o efeito observado em 2021-2024. Arredondado para 900.
MIN_N_AVALIACAO = 900
# Poder ~50% — registrado para que ninguém "descubra" depois que dava para
# olhar antes. Está aqui como referência, NÃO como ponto de avaliação.
N_PODER_MARGINAL = 440


def _params(inicio: str) -> dict[str, Any]:
    """A identidade CONGELADA do experimento. Mudar qualquer coisa aqui é trial
    nova — o registro do core recusa update com params diferentes, e é assim
    que o desenho fica realmente congelado."""
    return {
        "market": "1x2",
        "hypothesis": "a pilha de serving bate a climatologia em RPS numa coorte prospectiva",
        "engine": ENGINE,
        "ensemble_xg_enabled": False,
        "model": MODEL_TAG,
        "baseline": BASELINE,
        "retrain_every": RETRAIN_EVERY,
        "min_history": MIN_HISTORY,
        "block_guard": "kickoff (jogos simultâneos fora do treino um do outro)",
        "bootstrap": {"scheme": "moving", "block_length": BLOCK_LENGTH, "n_boot": N_BOOT, "seed": SEED},
        "primary_metric": "rps",
        "guardrails": list(GUARDRAIL_METRICS),
        "min_n_avaliacao": MIN_N_AVALIACAO,
        "avaliacoes_intermediarias": False,
        "league": "Brasileirão Série A",
        "cohort_start": inicio,
    }


def _notes(inicio: str) -> str:
    return (
        f"PRÉ-REGISTRO ({inicio}) — coorte PROSPECTIVA, dados ainda não existentes. "
        f"Hipótese: a pilha de serving (motor '{ENGINE}', ensemble_xg DESLIGADO) bate a "
        f"climatologia em RPS. GATE declarado antes dos dados: (1) IC95 do delta de RPS vs. "
        f"climatologia inteiramente abaixo de zero; (2) nenhum guardrail "
        f"({', '.join(GUARDRAIL_METRICS)}) materialmente pior, isto é, com IC95 inteiro do lado "
        f"ruim; (3) controle negativo do motor '{ENGINE}' passando na MESMA coorte. "
        f"PONTO ÚNICO de avaliação em n>={MIN_N_AVALIACAO}, SEM olhadas intermediárias "
        f"(n={N_PODER_MARGINAL} daria poder ~50% para o efeito observado em 2021-2024 e produziria "
        f"inconclusiva não-informativa; {MIN_N_AVALIACAO} dá ~80%). "
        f"MOTIVAÇÃO: em 2026-08-22 mediu-se RPS 0.213339 vs climatologia 0.219989, delta "
        f"-0.006650, IC95 [-0.010544, -0.002858] em 2021-2024, com controle negativo passando "
        f"(reports/benchmark_serving_noxg_2026-08-22.json, "
        f"reports/permutation_serving_2026-08-22.json). Esse resultado NÃO é confirmatório: a "
        f"amostra já tinha sido vista. 2025 permanece SELADO (Regra 7) — a arquitetura não está "
        f"congelada, a TRACK A não começou — e 2026 é exploratório (Regra 1). Por isso a única "
        f"amostra cega é o futuro. "
        f"NÃO AUTORIZA CAPITAL: hipótese de qualidade de modelo, não de mercado; o gate econômico "
        f"é separado e depende do market_no_vig, que não existe. Resultado ainda não medido."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="imprime o desenho e NÃO grava no registro")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    inicio = datetime.now(UTC).date().isoformat()
    params = _params(inicio)

    if args.dry_run:
        desenho = {"trial": TRIAL_NAME, "params": params, "notes": _notes(inicio)}
        print(json.dumps(desenho, ensure_ascii=False, indent=2))
        return 0

    attestation = attest_rps_power()
    log.info("atestado de poder emitido: fingerprint=%s", attestation["pipeline_fingerprint"])

    TrialRegistry(TRIALS).register(
        TRIAL_NAME,
        params=params,
        sharpe=None,
        notes=_notes(inicio),
        metric="rps",
        status="pre-registrada",
        pipeline_fingerprint=attestation["pipeline_fingerprint"],
        # Fim ABERTO: a coorte ainda está acumulando. O schema do core aceita um
        # dos lados None exatamente para isto.
        test_period=[inicio, None],
    )
    log.info("trial '%s' PRÉ-REGISTRADA (status='pre-registrada')", TRIAL_NAME)
    log.info("coorte começa em %s; avaliar SÓ quando n>=%d", inicio, MIN_N_AVALIACAO)
    log.info("NENHUMA medição foi feita — este script não olha dados, de propósito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
