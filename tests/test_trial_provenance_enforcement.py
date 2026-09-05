"""Toda trial com veredito FECHADO precisa de proveniência reproduzível.

Auditoria adversarial 2026-09-05, achado 1 (`docs/AUDITORIA_ADVERSARIAL_2026-09-05.md`,
issue #56): as 29 trials do registro têm `dataset_hash`, `seed`, `code_version`,
`data_cutoff` e `executed_at` iguais a `"UNKNOWN"`. O esquema
`trial-registry/2.0.0` define esses campos exatamente para permitir reprodução
independente, e `predictor_core` já exporta `dataset_fingerprint` e
`current_code_version` para preenchê-los — sem nenhum consumidor no domínio.

Este teste trava a porta daqui para frente. Ele NÃO tenta consertar o passado:
o `matches.db` de cada corrida histórica não é versionado e não tem hash em
lugar nenhum, então a proveniência dessas 29 é irrecuperável por construção. Em
vez de fingir o contrário, a lista abaixo as declara explicitamente como
historicamente não reproduzíveis — e qualquer trial NOVA com veredito fechado
falha aqui até trazer proveniência de verdade.

Consequência deliberada: para "resolver" uma falha deste teste não basta
adicionar o id na lista. A lista é congelada e um teste próprio impede que ela
cresça.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_V2 = ROOT / "data" / "trials.v2.json"

# Vereditos que fecham uma hipótese. `pre-registrada` e `exploratoria` estão
# fora: são desenhos abertos, ainda sem afirmação a sustentar.
VEREDITOS_FECHADOS = frozenset({"comprovada", "refutada", "inconclusiva", "informativa", "substituida"})

# Campos sem os quais um terceiro não refaz a corrida.
PROVENIENCIA_EXIGIDA = ("dataset_hash", "code_version", "seed", "data_cutoff", "executed_at")

# As 29 trials que já existiam quando a regra entrou (2026-09-05). O dado bruto
# que as originou não é recuperável; elas ficam registradas como o que são.
# ESTA LISTA NÃO CRESCE — ver test_a_lista_historica_nao_cresce.
HISTORICAS_IRREPRODUZIVEIS = frozenset(
    {
        "h1-ou25-edge-2-15-walkforward",
        "h2-periodo-1t-conf60",
        "h3-ou25-sombra-2026",
        "H4_DIXON_COLES_CALIBRATED",
        "h5-ensemble-xg-sombra-2026",
        "h3-ou25-sombra-pinnacle-2026",
        "h5-ensemble-xg-sombra-pinnacle-2026",
        "h1-ou25-walkforward-2023-2026-exploratoria",
        "h7-clv-prospectivo-pinnacle-2026",
        "h8-ou25-train-2023-2025-test-2026-observed",
        "h9-ou25-prospective-replication",
        "h11-refit-cadence-rodada-vs-100jogos",
        "h11-v2-refit10-vs-100-retrospective-reanalysis",
        "h15-refit10-vs-100-serving-v2-prospectivo",
        "h12-ensemble-xg-ligado-vs-desligado",
        "h13-serving-vs-climatologia-prospectivo",
        "market-03-edge-ordering-sofascore-diagnostic",
        "market-04-ou25-btts-resolution-and-ordering",
        "pit-absences-new-information",
        "pit-lineup-strength-new-information",
        "pit-isolated-xg-new-lineage",
        "pit-hierarchical-team-home-advantage",
        "live-backtest-viability-gate",
        "prospective-paper-validation-governance",
        "market-05-pinnacle-soft-structural-edge",
        "market-06-ou25-dev-only-ordering-triage",
        "observation-2026-inter-bahia-slow-reactivity",
        "market05-a1-shadow",
        "h14-serving-v2-vs-climatologia-prequential-prospectivo",
    }
)


def _trials() -> list[dict]:
    return json.loads(TRIALS_V2.read_text(encoding="utf-8"))


def test_a_lista_historica_nao_cresce() -> None:
    """O grandfathering é um fato de 2026-09-05, não uma válvula de escape.

    Sem esta trava, a forma mais fácil de silenciar a regressão de proveniência
    seria acrescentar o id da trial nova à lista — que é exatamente o defeito
    que o achado 1 descreve, agora com uma etapa a mais.
    """
    assert len(HISTORICAS_IRREPRODUZIVEIS) == 29, (
        "a lista de trials historicamente irreproduzíveis é congelada em 29 "
        "(estado de 2026-09-05). Trial nova com veredito fechado precisa de "
        "proveniência real, não de uma linha nova aqui."
    )


def test_toda_trial_historica_da_lista_ainda_existe() -> None:
    """Renomear uma trial não pode fazê-la sair da lista pela porta dos fundos."""
    ids = {t["trial_id"] for t in _trials()}
    sumidas = HISTORICAS_IRREPRODUZIVEIS - ids
    assert not sumidas, (
        f"trials da lista histórica desapareceram do registro: {sorted(sumidas)}. "
        "Renomear ou remover uma trial fechada apaga o registro de que ela existiu."
    )


def test_trial_nova_com_veredito_fechado_tem_proveniencia() -> None:
    """A regra propriamente dita: fechou veredito, tem que ser reproduzível."""
    faltando: dict[str, list[str]] = {}
    for trial in _trials():
        tid = trial["trial_id"]
        if tid in HISTORICAS_IRREPRODUZIVEIS:
            continue
        if trial.get("status") not in VEREDITOS_FECHADOS:
            continue
        vazios = [
            campo for campo in PROVENIENCIA_EXIGIDA if str(trial.get(campo, "UNKNOWN")).strip() in ("", "UNKNOWN")
        ]
        if vazios:
            faltando[tid] = vazios

    assert not faltando, (
        "trial com veredito fechado e proveniência ausente:\n  "
        + "\n  ".join(f"{tid}: {campos}" for tid, campos in sorted(faltando.items()))
        + "\n\npredictor_core exporta dataset_fingerprint() e current_code_version() "
        "justamente para preencher esses campos. Sem eles, o veredito não é "
        "verificável por terceiro — ver docs/AUDITORIA_ADVERSARIAL_2026-09-05.md."
    )


def test_o_estado_historico_esta_registrado_e_nao_escondido() -> None:
    """Documenta o tamanho do buraco, para ele não virar paisagem.

    Se alguém preencher a proveniência de uma trial histórica — o único caminho
    é recuperar o `matches.db` da corrida — este teste falha pedindo que ela
    saia da lista. Falhar por melhora é o comportamento desejado.
    """
    trials = {t["trial_id"]: t for t in _trials()}
    ainda_sem_proveniencia = {
        tid
        for tid in HISTORICAS_IRREPRODUZIVEIS
        if tid in trials
        and all(str(trials[tid].get(campo, "UNKNOWN")).strip() in ("", "UNKNOWN") for campo in PROVENIENCIA_EXIGIDA)
    }
    recuperadas = HISTORICAS_IRREPRODUZIVEIS & set(trials) - ainda_sem_proveniencia
    assert not recuperadas, (
        f"estas trials históricas ganharam proveniência: {sorted(recuperadas)}. "
        "Ótimo — remova-as de HISTORICAS_IRREPRODUZIVEIS e ajuste a contagem "
        "esperada em test_a_lista_historica_nao_cresce."
    )
