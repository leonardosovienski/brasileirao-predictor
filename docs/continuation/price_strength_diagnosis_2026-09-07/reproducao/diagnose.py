"""Describe frozen 2025 successes and failures; no model fit or new backtest.

Only this study's prior exports are read. Bins are the task's prespecified
partitions. Existing bets are classified and accounted for, never reselected.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
SOURCE = WORKSPACE / "outputs" / "TESTE_XG_REAL"
OUTPUT = WORKSPACE / "outputs" / "DIAGNOSTICO_XG"
PLAN_SHA = "507c69fc01aaabd9d78734b1153f740c3c347f601f5b1609cd54839a1698aaaa"
CAL, RAW, OLD, MARKET = ("xg_calibrated_primary", "xg_raw_diagnostic", "old_raw_frozen_2024", "market_proportional_devig")
ARMS = (CAL, RAW, OLD, MARKET)
SIDES = {"1x2": ("home", "draw", "away"), "ou25": ("over", "under"), "btts": ("yes", "no")}
P_BINS = ((0, .2, "0-.2"), (.2, .4, ".2-.4"), (.4, .6, ".4-.6"), (.6, .8, ".6-.8"), (.8, 1, ".8-1"))
ODDS_BINS = ((1, 2, "1-2"), (2, 3, "2-3"), (3, 5, "3-5"), (5, math.inf, "5+"))
TRANSITIONS = ("same_bet", "changed_bet", "raw_only", "calibrated_only", "neither")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


def mean(values):
    return math.fsum(values) / len(values) if values else None


def same_number(left, right):
    assert math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-10), (left, right)


def band(value, bins):
    for lower, upper, label in bins:
        if lower <= value < upper or upper == 1 and value == 1:
            return label
    raise AssertionError(f"Value outside prescribed bins: {value}")


def actual_sides(row):
    h, a = row["outcome"]["home_goals"], row["outcome"]["away_goals"]
    return {"1x2": "home" if h > a else "away" if a > h else "draw",
            "ou25": "over" if h + a >= 3 else "under", "btts": "yes" if h > 0 and a > 0 else "no"}


def selected_records(rows, arm):
    records = []
    for row in rows:
        bet = row["bets"][arm]
        if bet is None:
            continue
        candidate, settlement = bet["candidate"], bet["settlement"]
        market, side = candidate["market"], candidate["side"]
        won = actual_sides(row)[market] == side
        assert won == settlement["won"]
        gross = candidate["odd"] - 1 if won else -1.0
        same_number(gross - .02, settlement["net_profit_units"])
        records.append({
            "event_id": row["event_id"], "kickoff": row["kickoff"], "home": row["home"], "away": row["away"],
            "outcome": row["outcome"], "market": market, "side": side, "odd": candidate["odd"],
            "probability": candidate["probability"], "market_probability": row["probabilities"][MARKET][market][side],
            "predicted_net_ev": candidate["predicted_net_ev"], "won": won,
            "gross_profit_units": gross, "cost_units": .02, "net_profit_units": gross - .02,
            "probability_bin": band(candidate["probability"], P_BINS), "odds_bin": band(candidate["odd"], ODDS_BINS),
        })
    return records


def summarize(records):
    n = len(records)
    gross = math.fsum(row["gross_profit_units"] for row in records)
    net = math.fsum(row["net_profit_units"] for row in records)
    observed = mean([float(row["won"]) for row in records])
    model = mean([row["probability"] for row in records])
    market = mean([row["market_probability"] for row in records])
    return {
        "n": n, "wins": sum(row["won"] for row in records), "losses": sum(not row["won"] for row in records),
        "stake_units": n, "gross_profit_units": gross, "cost_units": .02 * n, "net_profit_units": net,
        "net_roi": net / n if n else None, "mean_probability": model, "observed_hit_rate": observed,
        "mean_market_probability_same_selection": market, "mean_odd": mean([row["odd"] for row in records]),
        "model_probability_minus_hit_rate": model - observed if n else None,
        "market_probability_minus_hit_rate": market - observed if n else None,
        "mean_predicted_net_ev": mean([row["predicted_net_ev"] for row in records]),
        "sum_predicted_net_ev": math.fsum(row["predicted_net_ev"] for row in records),
        "selection_brier_model": mean([(row["probability"] - row["won"]) ** 2 for row in records]),
        "selection_brier_market": mean([(row["market_probability"] - row["won"]) ** 2 for row in records]),
    }


def partition(records, key, levels):
    grouped = {level: summarize([row for row in records if key(row) == level]) for level in levels}
    assert sum(group["n"] for group in grouped.values()) == len(records)
    same_number(math.fsum(group["net_profit_units"] for group in grouped.values()),
                math.fsum(row["net_profit_units"] for row in records))
    return grouped


def concentration(records):
    wins = sorted([row for row in records if row["won"]], key=lambda row: (-row["net_profit_units"], row["kickoff"], row["event_id"]))
    losses = sorted([row for row in records if not row["won"]], key=lambda row: (row["net_profit_units"], row["kickoff"], row["event_id"]))
    winner_total = math.fsum(row["net_profit_units"] for row in wins)
    loser_total = math.fsum(row["net_profit_units"] for row in losses)
    return {
        "top_five_wins": wins[:5], "top_five_losses_with_chronological_tie_break": losses[:5],
        "all_losses_equal_minus_1_02": all(abs(row["net_profit_units"] + 1.02) < 1e-12 for row in losses),
        "largest_loss_tie_count": len(losses), "all_wins_net_units": winner_total, "all_losses_net_units": loser_total,
        "top_five_wins_net_units": math.fsum(row["net_profit_units"] for row in wins[:5]),
        "top_five_wins_share_of_positive_payments": math.fsum(row["net_profit_units"] for row in wins[:5]) / winner_total if wins else None,
        "top_five_losses_net_units": math.fsum(row["net_profit_units"] for row in losses[:5]),
        "top_five_losses_share_of_absolute_losses": min(5, len(losses)) / len(losses) if losses else None,
        "note": "Equal flat-stake losses are not individually causal explanations; top wins describe concentration only.",
    }


def transition_analysis(rows):
    entries = []
    for row in rows:
        raw, cal = row["bets"][RAW], row["bets"][CAL]
        if raw is None and cal is None:
            category = "neither"
        elif raw is None:
            category = "calibrated_only"
        elif cal is None:
            category = "raw_only"
        else:
            old_key = tuple(raw["candidate"][field] for field in ("market", "side", "odd"))
            new_key = tuple(cal["candidate"][field] for field in ("market", "side", "odd"))
            category = "same_bet" if old_key == new_key else "changed_bet"
        raw_net = raw["settlement"]["net_profit_units"] if raw else 0.0
        cal_net = cal["settlement"]["net_profit_units"] if cal else 0.0
        entries.append({"event_id": row["event_id"], "kickoff": row["kickoff"], "home": row["home"], "away": row["away"],
                        "outcome": row["outcome"], "category": category, "raw_bet": raw, "calibrated_bet": cal,
                        "raw_net_units": raw_net, "calibrated_net_units": cal_net, "delta_cal_minus_raw_units": cal_net - raw_net})
    grouped = {}
    for category in TRANSITIONS:
        selected = [row for row in entries if row["category"] == category]
        grouped[category] = {
            "fixtures": len(selected), "raw_bets": sum(row["raw_bet"] is not None for row in selected),
            "calibrated_bets": sum(row["calibrated_bet"] is not None for row in selected),
            "raw_net_units": math.fsum(row["raw_net_units"] for row in selected),
            "calibrated_net_units": math.fsum(row["calibrated_net_units"] for row in selected),
            "delta_cal_minus_raw_units": math.fsum(row["delta_cal_minus_raw_units"] for row in selected),
            "improved_event_payments": sum(row["delta_cal_minus_raw_units"] > 1e-12 for row in selected),
            "worsened_event_payments": sum(row["delta_cal_minus_raw_units"] < -1e-12 for row in selected),
            "equal_event_payments": sum(abs(row["delta_cal_minus_raw_units"]) <= 1e-12 for row in selected),
        }
    delta = math.fsum(row["delta_cal_minus_raw_units"] for row in entries)
    same_number(delta, math.fsum(group["delta_cal_minus_raw_units"] for group in grouped.values()))
    return {"groups": grouped, "total_delta_cal_minus_raw_units": delta, "event_transitions": entries,
            "five_largest_improvements": sorted(entries, key=lambda row: (-row["delta_cal_minus_raw_units"], row["kickoff"], row["event_id"]))[:5],
            "five_largest_deteriorations": sorted(entries, key=lambda row: (row["delta_cal_minus_raw_units"], row["kickoff"], row["event_id"]))[:5]}


def forecast_diagnosis(rows, forecasts):
    by_id = {row["event_id"]: row for row in forecasts}
    result = {"rates": {}, "probability_shift_cal_minus_raw": {}, "unconditional_class_calibration": {}}
    for where in ("home", "away"):
        raw_values = [by_id[row["event_id"]]["raw"][f"lambda_{where}"] for row in rows]
        cal_values = [by_id[row["event_id"]]["calibrated"][f"lambda_{where}"] for row in rows]
        result["rates"][where] = {"mean_raw_lambda": mean(raw_values), "mean_calibrated_lambda": mean(cal_values),
                                  "mean_actual_goals": mean([row["outcome"][f"{where}_goals"] for row in rows]),
                                  "mean_change": mean([cal - raw for cal, raw in zip(cal_values, raw_values)])}
    for market, sides in SIDES.items():
        result["probability_shift_cal_minus_raw"][market] = {}
        for side in sides:
            shifts = [row["probabilities"][CAL][market][side] - row["probabilities"][RAW][market][side] for row in rows]
            result["probability_shift_cal_minus_raw"][market][side] = {
                "mean_delta": mean(shifts), "increased": sum(value > 1e-12 for value in shifts),
                "decreased": sum(value < -1e-12 for value in shifts), "unchanged": sum(abs(value) <= 1e-12 for value in shifts)}
        for arm in ARMS:
            classes = result["unconditional_class_calibration"].setdefault(arm, {}).setdefault(market, {})
            for side in sides:
                observed = mean([float(actual_sides(row)[market] == side) for row in rows])
                predicted = mean([row["probabilities"][arm][market][side] for row in rows])
                classes[side] = {"n": len(rows), "mean_probability": predicted, "observed_frequency": observed,
                                 "prediction_minus_frequency": predicted - observed}
    return result


def percentage(value):
    return "—" if value is None else f"{100 * value:.2f}%"


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
                     + ["| " + " | ".join(str(value) for value in row) + " |" for row in rows])


def markdown(report):
    arms = report["arms"]
    parts = ["# Diagnóstico dos erros e acertos do xG em 2025", "",
             "Decomposição descritiva dos resultados já congelados e auditados. Nenhuma nova previsão, aposta, calibração ou regra foi calculada. As apostas citadas são pagamentos hipotéticos em odds agregadas retrospectivas.", "",
             "O calibrado principal terminou pior financeiramente que o xG bruto. A decomposição abaixo mostra quais decisões mudaram; ela não prova que a calibração causou o placar de cada jogo nem autoriza escolher uma política pelos resultados vistos.", "",
             table(["Modelo", "Apostas", "Acertos/erros", "Saldo líquido", "ROI", "p prevista", "Taxa real", "p mercado da seleção"], [
                 [arm, arms[arm]["all_bets"]["n"], f"{arms[arm]['all_bets']['wins']}/{arms[arm]['all_bets']['losses']}",
                  f"{arms[arm]['all_bets']['net_profit_units']:+.3f}u", percentage(arms[arm]["all_bets"]["net_roi"]),
                  percentage(arms[arm]["all_bets"]["mean_probability"]), percentage(arms[arm]["all_bets"]["observed_hit_rate"]),
                  percentage(arms[arm]["all_bets"]["mean_market_probability_same_selection"])] for arm in ARMS]), "",
             "## O que mudou ao aplicar a calibração", "",
             table(["Transição", "Jogos", "Saldo raw", "Saldo calibrado", "Diferença cal−raw"], [
                 [category, group["fixtures"], f"{group['raw_net_units']:+.3f}u", f"{group['calibrated_net_units']:+.3f}u",
                  f"{group['delta_cal_minus_raw_units']:+.3f}u"] for category, group in report["raw_to_calibrated"]["groups"].items()]), "",
             f"A soma exata das entradas, saídas e trocas é {report['raw_to_calibrated']['total_delta_cal_minus_raw_units']:+.3f}u. Apostas mantidas recebem o mesmo pagamento, mesmo quando a probabilidade mudou.", "",
             f"Escalas congeladas em 2024: mandante {report['calibration_metadata']['home_scale']:.6f}; visitante {report['calibration_metadata']['away_scale']:.6f}. Isso altera as taxas de gols e pode alterar a ordenação das apostas; o ajuste não foi escolhido usando estes resultados de 2025.", "",
             table(["Taxa", "Lambda raw média", "Lambda calibrada média", "Gols observados médios"], [
                 [side, f"{values['mean_raw_lambda']:.4f}", f"{values['mean_calibrated_lambda']:.4f}", f"{values['mean_actual_goals']:.4f}"]
                 for side, values in report["forecast_diagnosis"]["rates"].items()])]
    for arm in ARMS[:3]:
        data = arms[arm]
        parts.extend(["", f"## {arm}", "", "Todos os mercados e lados aparecem, inclusive os sem apostas.", "",
                      table(["Mercado/lado", "n", "Acertos", "Erros", "Saldo", "ROI", "p prevista", "Taxa real", "p mercado"], [
                          [label, stats["n"], stats["wins"], stats["losses"], f"{stats['net_profit_units']:+.3f}u",
                           percentage(stats["net_roi"]), percentage(stats["mean_probability"]), percentage(stats["observed_hit_rate"]),
                           percentage(stats["mean_market_probability_same_selection"])] for label, stats in data["by_market_side"].items()]), "",
                      "Faixas fixadas no pedido. Intervalos fechados à esquerda e abertos à direita; a última faixa de probabilidade inclui 1.", ""])
        for label, bins in (("Probabilidade", data["by_probability_bin"]), ("Odd", data["by_odds_bin"])):
            parts.extend([table([label, "n", "Acertos/erros", "Saldo", "p prevista", "Taxa real", "p mercado"], [
                [key, stats["n"], f"{stats['wins']}/{stats['losses']}", f"{stats['net_profit_units']:+.3f}u",
                 percentage(stats["mean_probability"]), percentage(stats["observed_hit_rate"]),
                 percentage(stats["mean_market_probability_same_selection"])] for key, stats in bins.items()]), ""])
        parts.extend(["Acertos e erros separados: as taxas reais de 100% e 0% são consequência dessa separação, não evidência de calibração.", "",
                      table(["Grupo", "n", "Saldo", "p prevista média", "p mercado média"], [
                          [label, data[label]["n"], f"{data[label]['net_profit_units']:+.3f}u", percentage(data[label]["mean_probability"]),
                           percentage(data[label]["mean_market_probability_same_selection"])] for label in ("wins", "losses")]), ""])
        concentration = data["concentration"]
        parts.extend([f"Os cinco maiores acertos somam {concentration['top_five_wins_net_units']:+.3f}u, ou {percentage(concentration['top_five_wins_share_of_positive_payments'])} dos pagamentos líquidos positivos. Todas as {concentration['largest_loss_tie_count']} derrotas custam exatamente 1,02u; não existe uma derrota individual mais cara neste desenho.", "",
                      table(["Cinco maiores acertos", "Seleção", "Odd", "p modelo", "p mercado", "Saldo"], [
                          [f"{row['home']} × {row['away']} ({row['event_id']})", f"{row['market']}/{row['side']}", row["odd"],
                           percentage(row["probability"]), percentage(row["market_probability"]), f"{row['net_profit_units']:+.3f}u"]
                          for row in concentration["top_five_wins"]])])
    parts.extend(["", "## Incerteza já publicada", "", "Os intervalos abaixo são os mesmos da avaliação congelada; não foram recalculados para procurar subgrupos positivos.", "",
                  table(["Comparação", "Δ pagamento por jogo", "IC95 semanal descritivo"], [
                      [f"{candidate} − {baseline}", f"{values['delta_profit_per_fixture']:+.4f}u",
                       f"[{values['ci95_weekly_descriptive'][0]:+.4f}; {values['ci95_weekly_descriptive'][1]:+.4f}]u"]
                      for candidate, comparisons in report["existing_confidence_intervals"]["economics"].items()
                      for baseline, values in comparisons.items()]), "",
                  "## Implicações para uma correção futura", "",
                  "A diferença entre probabilidade prevista, mercado e frequência nas seleções deve ser examinada junto das perdas probabilísticas de todos os jogos. Melhorar Brier médio e melhorar o ranking das apostas são objetivos distintos. As tabelas identificam concentração e desvios descritivos; faixas positivas não são recomendações de filtro.", "",
                  "Convém verificar a especificação da calibração de taxas, sua função objetivo e como a redução de gols visitantes desloca home/draw/away, under e ambas não. Qualquer alteração exige outro candidato declarado e escolha com dados anteriores à avaliação; não ajustar escalas ou excluir mercados porque perderam nesta amostra.", "",
                  "Verificar também a proveniência do xG e das odds: atraso de 48h é uma hipótese, e preços agregados não atestam casa nem aceitação. O comparador entre casas permanece sem teste econômico com capturas elegíveis.", "",
                  "O JSON contém todas as transições por evento, os cinco maiores efeitos positivos e negativos das trocas, calibração por classe, contagens de deslocamentos de probabilidade e estratos completos. Esses registros permitem reproduzir a decomposição sem recomputar o modelo.", "",
                  "## Limitações", "", *[f"- {item}" for item in report["limitations"]], ""])
    return "\n".join(parts)


def main():
    names = ("PLANO.json", "results.json", "event_results.json", "forecasts.json", "panel.json", "audit.json")
    source_hashes = {name: digest(SOURCE / name) for name in names}
    assert source_hashes["PLANO.json"] == PLAN_SHA
    manifest = load("MANIFEST.json")
    for name in names:
        if name in manifest["files"]:
            assert source_hashes[name] == manifest["files"][name], name
    assert load("audit.json")["status"] == "PASS"
    rows, results, forecasts = load("event_results.json"), load("results.json"), load("forecasts.json")
    assert len(rows) == results["coverage"]["common_panel"] == 368
    assert all(datetime.fromisoformat(row["kickoff"]).year == 2025 for row in rows)
    assert len({row["event_id"] for row in rows}) == len(rows)
    arms = {}
    for arm in ARMS:
        selected = selected_records(rows, arm)
        overall = summarize(selected)
        assert overall["n"] == results["economics"][arm]["bets"]
        for field in ("wins", "losses", "gross_profit_units", "cost_units", "net_profit_units"):
            same_number(overall[field], results["economics"][arm][field])
        arms[arm] = {"all_bets": overall, "wins": summarize([row for row in selected if row["won"]]),
                     "losses": summarize([row for row in selected if not row["won"]]),
                     "by_market": partition(selected, lambda row: row["market"], SIDES),
                     "by_market_side": partition(selected, lambda row: row["market"] + "/" + row["side"],
                                                 [market + "/" + side for market, sides in SIDES.items() for side in sides]),
                     "by_probability_bin": partition(selected, lambda row: row["probability_bin"], [b[2] for b in P_BINS]),
                     "by_odds_bin": partition(selected, lambda row: row["odds_bin"], [b[2] for b in ODDS_BINS]),
                     "concentration": concentration(selected)}
    transitions = transition_analysis(rows)
    same_number(transitions["total_delta_cal_minus_raw_units"],
                results["economics"][CAL]["net_profit_units"] - results["economics"][RAW]["net_profit_units"])
    report = {
        "schema_version": "rolling-xg-frozen-diagnosis/1", "status": "POST_HOC_DESCRIPTIVE_NO_POLICY_SELECTION",
        "generated_at_utc": datetime.now(UTC).isoformat(), "program_sha256": digest(Path(__file__)),
        "input_sha256": source_hashes, "evaluation_plan_sha256": PLAN_SHA, "coverage": results["coverage"],
        "fixed_bins": {"probability": [b[2] for b in P_BINS], "odds": [b[2] for b in ODDS_BINS],
                       "boundary_rule": "left-inclusive right-exclusive; probability 1 included in final bin"},
        "arms": arms, "raw_to_calibrated": transitions, "forecast_diagnosis": forecast_diagnosis(rows, forecasts),
        "calibration_metadata": {key: results["calibration"][key] for key in
                                 ("n_matches", "home_scale", "away_scale", "training_end", "calibration_end", "availability_policy")},
        "all_fixture_probabilistic_metrics": results["probabilistic"], "existing_confidence_intervals": results["bootstrap"],
        "real_capital_enabled": False, "execution_proven": False, "new_forecasts_or_backtest_run": False,
        "limitations": [
            "2025 já foi observado e explorado; este diagnóstico posterior não cria holdout independente.",
            "As faixas e comparações são descritivas, sem intervalos novos por subgrupo nem correção por buscas anteriores.",
            "Frequências condicionadas a acerto ou erro são 1 ou 0 por construção; não identificam calibração.",
            "Um acerto não prova qualidade da previsão e uma derrota não identifica a causa do erro.",
            "Os pagamentos usam 1u e custo fixo 0,02u; odds retrospectivas agregadas não comprovam execução real.",
            "Disponibilidade do xG após 48h é assumida, sem trilha histórica de publicação ou revisão.",
            "Comparar candidatos muda a política completa; o ganho ou a perda não identifica isoladamente o efeito causal do xG.",
            "Intervalos semanais publicados são descritivos e não corrigem busca anterior nem incerteza do ajuste.",
            "Não selecionar mercados, faixas, escalas ou limiares a partir dos saldos aqui exibidos.",
        ],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "diagnostico.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    with (OUTPUT / "ACHADOS.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown(report))
    print(json.dumps({"status": report["status"], "fixtures": len(rows),
                      "transition_counts": {key: value["fixtures"] for key, value in transitions["groups"].items()},
                      "net_difference_cal_minus_raw": transitions["total_delta_cal_minus_raw_units"]}))


if __name__ == "__main__":
    main()
