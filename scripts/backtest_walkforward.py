"""Backtest WALK-FORWARD do Brasileirão (PASSO 4 do bootstrap do domínio).

Diferença para `python -m src.backtest` (params frozen numa única janela):
aqui a base 2024-2025 é dividida em BLOCOS de rodadas (config
backtest.walk_forward_window_rounds; 19 rodadas = 1 turno = ~190 jogos) e os
parâmetros do modelo de gols são recalibrados ANTES de cada bloco, só com
jogos passados — nenhum bloco enxerga o próprio futuro. O Elo já é forward
por construção (compute_ratings).

O funil de aposta é o MESMO do src.backtest (reuso de _load_odds/_find_odds/
_settle): gatilho = edge vs preço na janela [min_edge, max_edge], stake fixo,
CLV = odd pactuada × Shin do fechamento − 1.

H2 (picks de período 1T) roda em paralelo: fração de gols do 1T calibrada só
com jogos ANTERIORES ao bloco, pick = seleção de O/U 1T com prob ≥ 0.60,
aferida contra o placar de intervalo real (home_score_ht). SEM odds de período
na base → sem ROI/CLV; a métrica é acurácia/calibração (mesmo status
"informativa" da Copa).

Saídas:
  data/backtest_bets_walkforward.csv   — ledger H1 (todos os mercados)
  data/period_picks_walkforward.csv    — picks H2 aferidos
  data/walkforward_summary.json        — métricas + veredito GO/NO-GO

Critério GO (o mesmo da Copa, sobre a população alvo de H1 = OU2.5):
  PSR ≥ 0.80, IC95_lower(pnl médio) > 0, DSR ≥ 0.95 (descontado pelo registro
  de tentativas em data/trials.json).

Banco em modo somente-leitura (P12): este script é de pesquisa.
"""

import csv
import json
import statistics as st
import sys
from datetime import date, timedelta
from pathlib import Path

from predictor_core.measurement.bootstrap import bootstrap_ci
from predictor_core.measurement.stats import probabilistic_sharpe_ratio
from predictor_core.measurement.trials import TrialRegistry

from src import db, model, ratings
from src.backtest import (
    _find_event,
    _find_odds,
    _load_ext_index,
    _load_flat_markets,
    _load_lines,
    _load_odds,
    _settle,
    _settle_extended,
)
from src.ingest import load_config
from src.math_utils import shin_probabilities
from src.research.temporal_replay import build_temporal_manifest

ROOT = Path(__file__).resolve().parent.parent
OUTCOMES = ("home", "draw", "away")
GAMES_PER_ROUND = 10  # Série A: 20 clubes → 10 jogos por rodada
H2_CONF = 0.60  # pick de período: confiança mínima pré-registrada
H2_LINES = (1.5, 2.5)  # linhas de O/U do 1T aferíveis com o placar de HT


def _aligned_blocks(rows, target_games: int) -> list[tuple[int, int]]:
    """Build expanding test blocks without splitting a date batch."""
    boundaries = [0]
    for index in range(1, len(rows)):
        if str(rows[index][0])[:10] != str(rows[index - 1][0])[:10]:
            boundaries.append(index)
    boundaries.append(len(rows))
    blocks: list[tuple[int, int]] = []
    start = 0
    while start < len(rows):
        candidates = [boundary for boundary in boundaries if boundary > start and boundary - start >= target_games]
        end = candidates[0] if candidates else len(rows)
        blocks.append((start, end))
        start = end
    return blocks


def _ht_fraction(rows_ht, cut_date):
    """Fração média de gols no 1T usando SÓ jogos com HT anteriores a cut_date.
    Espelha display.ht_goal_fraction, mas forward-only (sem lookahead).
    None se n < 50 (mesmo piso do serving)."""
    tot_ht = tot_ft = n = 0
    for d, hs, as_, hht, aht in rows_ht:
        if d >= cut_date or hht is None or aht is None:
            continue
        ft = hs + as_
        if ft == 0:
            continue
        tot_ht += hht + aht
        tot_ft += ft
        n += 1
    if n < 50 or tot_ft == 0:
        return None, n
    return tot_ht / tot_ft, n


def run_walkforward(cfg, conn):
    bt = cfg.get("backtest", {})
    min_edge = float(bt.get("min_edge", 0.0))
    max_edge = float(bt.get("max_edge", 1.0))
    ou_line = float(bt.get("over_under_line", 2.5))
    block_games = int(bt.get("walk_forward_window_rounds", 19)) * GAMES_PER_ROUND
    max_goals = cfg["model"]["max_goals"]
    cal_years = cfg["model"].get("calibration_window_years", 4)

    rows = db.completed_matches_with_kickoff(conn)
    if len(rows) < 2 * block_games:
        sys.exit(f"base insuficiente: {len(rows)} jogos < 2 blocos de {block_games}")

    window = cfg["elo"].get("window_years")
    if window:
        cut = (date.fromisoformat(rows[-1][0]) - timedelta(days=int(window * 365.25))).isoformat()
        rows = [r for r in rows if r[0] >= cut]
    _, history = ratings.compute_ratings(rows, cfg["elo"])

    odds = _load_odds(conn)
    if not odds:
        sys.exit("sem odds no banco — rode python -m src.ingest_sofascore")
    ext_index = _load_ext_index(conn)
    flat_markets = _load_flat_markets(conn)
    line_markets = _load_lines(conn)

    # HT scores p/ H2 (chave date+times — mesma base sofascore, nomes idênticos)
    ht = {}
    for d, h, a, hht, aht in conn.execute(
        "SELECT date, home_team, away_team, home_score_ht, away_score_ht "
        "FROM sofascore_matches WHERE home_score_ht IS NOT NULL"
    ):
        ht[(d, h, a)] = (hht, aht)
    rows_ht = [(r[0], r[3], r[4], *ht.get((r[0], r[1], r[2]), (None, None))) for r in rows]

    # blocos: o primeiro é burn-in (Elo converge, calibração acumula), nunca testado
    aligned = _aligned_blocks(rows, block_games)
    blocks = aligned[1:]

    ledger, h2_picks = [], []
    for bi, (lo, hi) in enumerate(blocks, 1):
        first_date = rows[lo][0]
        cal_cut = (date.fromisoformat(first_date) - timedelta(days=int(cal_years * 365.25))).isoformat()
        cal_pairs = [(h, r) for h, r in zip(history, rows) if cal_cut <= r[0] < first_date]
        hist_cal = [h for h, _r in cal_pairs]
        if len(hist_cal) < 100:
            print(f"bloco {bi}: só {len(hist_cal)} jogos de calibração — pulado")
            continue
        weights = model.exponential_recency_weights(
            [r[0] for _h, r in cal_pairs], first_date, cfg["model"]["goal_half_life_days"]
        )
        params = model.fit_goal_model(hist_cal, sample_weights=weights)
        frac1, n_frac = _ht_fraction(rows_ht, first_date)

        for i in range(lo, hi):
            d, home, away, hs, as_, tournament, neutral = rows[i]
            diff = history[i][0]
            r = model.predict_match(diff, 0.0, params, 0.0, max_goals=max_goals)
            total = hs + as_
            res_1x2 = "home" if hs > as_ else ("draw" if hs == as_ else "away")
            res_ou = "over" if total > ou_line else "under"
            ctx = {
                "date": d,
                "competition": tournament,
                "home": home,
                "away": away,
                "elo_diff": round(diff, 1),
                "lambda_home": round(r["lambda_a"], 3),
                "lambda_away": round(r["lambda_b"], 3),
                "score": f"{hs}-{as_}",
            }

            found = _find_odds(odds, home, away, d)
            if found:
                (oh, od_, oa), (o_over, o_under), x12_open, ou_open = found
                if None not in (oh, od_, oa):
                    ctx["result"] = res_1x2
                    p1x2 = {"home": r["p_win"], "draw": r["p_draw"], "away": r["p_loss"]}
                    closed = {"home": oh, "draw": od_, "away": oa}
                    opened = {"home": x12_open[0], "draw": x12_open[1], "away": x12_open[2]}
                    sh, _z, _ov = shin_probabilities([oh, od_, oa])
                    p_shin = {"home": sh[0], "draw": sh[1], "away": sh[2]}
                    for sel in OUTCOMES:
                        bet = _settle(
                            "1x2",
                            sel,
                            p1x2[sel],
                            p_shin[sel],
                            opened[sel],
                            closed[sel],
                            int(sel == res_1x2),
                            ctx,
                            min_edge,
                            max_edge,
                        )
                        if bet:
                            bet["block"] = bi
                            bet["params_mode"] = "walk_forward"
                            ledger.append(bet)
                if o_over and o_under:
                    p_over = r["over"].get(ou_line)
                    if p_over is not None:
                        ctx["result"] = res_ou
                        sh_ou, _z2, _ov2 = shin_probabilities([o_over, o_under])
                        for sel, p_m, o_op, o_cl, sp in (
                            ("over", p_over, ou_open[0], o_over, sh_ou[0]),
                            ("under", 1.0 - p_over, ou_open[1], o_under, sh_ou[1]),
                        ):
                            bet = _settle(
                                "ou25",
                                sel,
                                p_m,
                                sp,
                                o_op,
                                o_cl,
                                int(sel == res_ou),
                                ctx,
                                min_edge,
                                max_edge,
                            )
                            if bet:
                                bet["block"] = bi
                                bet["params_mode"] = "walk_forward"
                                ledger.append(bet)
                ev = _find_event(ext_index, home, away, d)
                if ev and None not in (oh, od_, oa):
                    eid, home_oriented = ev
                    n_before = len(ledger)
                    _settle_extended(
                        r,
                        eid,
                        home_oriented,
                        flat_markets,
                        line_markets,
                        ctx,
                        res_1x2,
                        hs,
                        as_,
                        total,
                        oh,
                        od_,
                        oa,
                        ou_line,
                        min_edge,
                        max_edge,
                        ledger,
                    )
                    for b in ledger[n_before:]:
                        b["block"] = bi
                        b["params_mode"] = "walk_forward"

            # ---- H2: pick de período (1T), forward-only, sem odds ----
            hht, aht = ht.get((d, home, away), (None, None))
            if frac1 is not None and hht is not None:
                rp = model.predict_remaining(diff, 0.0, params, 0.0, fraction=frac1, max_goals=max_goals)
                ht_total = hht + aht
                for line in H2_LINES:
                    p_over_1t = rp["over"].get(line)
                    if p_over_1t is None:
                        continue
                    for sel, p in (("over", p_over_1t), ("under", 1.0 - p_over_1t)):
                        if p < H2_CONF:
                            continue
                        won = int((ht_total > line) if sel == "over" else (ht_total < line))
                        h2_picks.append(
                            {
                                "block": bi,
                                "date": d,
                                "home": home,
                                "away": away,
                                "market": f"ou{line}_1T",
                                "selection": sel,
                                "model_prob": round(p, 4),
                                "ht_total": ht_total,
                                "won": won,
                                "frac1": round(frac1, 4),
                                "n_frac": n_frac,
                            }
                        )
    return ledger, h2_picks, len(blocks)


def _mkt_line(label, bets):
    n = len(bets)
    if not n:
        return {"n": 0}
    pnl = sum(b["pnl"] for b in bets)
    wins = sum(b["won"] for b in bets)
    clv_open = [b["clv"] for b in bets if b["bet_at"] == "open"]
    out = {
        "n": n,
        "wins": wins,
        "hit": round(wins / n, 4),
        "pnl": round(pnl, 2),
        "roi": round(pnl / n, 4),
        "n_open": len(clv_open),
        "clv_open_mean": round(st.mean(clv_open), 4) if clv_open else None,
    }
    print(
        f"  {label:<10}{n:>5} apostas {wins:>4} acertos ({wins / n:>5.1%}) "
        f"{pnl:>+8.2f}u  ROI {pnl / n:>+7.1%}"
        + (f"  CLV(open n={len(clv_open)}) {st.mean(clv_open):+.2%}" if clv_open else "  CLV(open) —")
    )
    return out


def main():
    cfg = load_config()
    conn = db.connect(str(ROOT / cfg["database"]), read_only=True)
    ledger, h2_picks, n_blocks = run_walkforward(cfg, conn)

    print(f"\nWALK-FORWARD — {n_blocks} blocos ({cfg['backtest'].get('walk_forward_window_rounds', 19)} rodadas/bloco)")
    print(
        f"total: {len(ledger)} apostas de valor no funil "
        f"[{cfg['backtest']['min_edge']:.0%}, {cfg['backtest']['max_edge']:.0%}]"
    )
    temporal_manifest = build_temporal_manifest(
        [
            {"date": row[0], "home_team": row[1], "away_team": row[2]}
            for row in conn.execute(
                "SELECT date, home_team, away_team FROM matches WHERE home_score IS NOT NULL ORDER BY date"
            ).fetchall()
        ]
    )
    summary = {
        "n_blocks": n_blocks,
        "n_bets": len(ledger),
        "markets": {},
        "temporal_policy": temporal_manifest["temporal_policy"],
        "temporal_source_sha256": temporal_manifest["source_sha256"],
        "temporal_group_count": temporal_manifest["group_count"],
    }
    print("\npor mercado:")
    for mkt in sorted({b["market"] for b in ledger}):
        summary["markets"][mkt] = _mkt_line(mkt, [b for b in ledger if b["market"] == mkt])

    # ---- H1: veredito sobre a população alvo (OU2.5) ----
    h1 = [b for b in ledger if b["market"] == "ou25"]
    returns = [b["pnl"] for b in h1]
    verdict = {"population": "ou25", "n": len(h1)}
    if len(returns) >= 30:
        psr = probabilistic_sharpe_ratio(returns, 0.0)
        # bootstrap por CLUSTER de jogo (mesma lição da auditoria da Copa:
        # over+under do mesmo jogo não são independentes)
        lo, hi, _boots = bootstrap_ci(
            h1,
            lambda bets: st.mean(b["pnl"] for b in bets),
            scheme="cluster",
            cluster_key=lambda b: (b["date"], b["home"], b["away"]),
            n_boot=int(cfg["backtest"].get("bootstrap_iterations", 1000)),
            seed=int(cfg["backtest"].get("bootstrap_seed", 13)),
        )
        if lo is None:
            verdict["verdict"] = "NO-GO"
            verdict["motivo"] = "bootstrap sem reamostra válida"
            print("\nH1: NO-GO — bootstrap sem reamostra válida")
            summary["h1"] = verdict
            lo = hi = float("nan")
        registry = TrialRegistry(ROOT / "data" / "trials.json")
        sr = st.mean(returns) / st.stdev(returns) if st.stdev(returns) else 0.0
        dsr_info = registry.deflated_sharpe(returns)
        verdict.update(
            {
                "sharpe_per_bet": round(sr, 4),
                "psr": round(psr, 4),
                "ic95_pnl_medio": [round(lo, 4), round(hi, 4)],
                "dsr": round(dsr_info["dsr"], 4),
                "sr0": round(dsr_info["sr0"], 4),
                "n_trials": dsr_info["n_trials"],
            }
        )
        go = psr >= 0.80 and lo is not None and lo > 0 and dsr_info["dsr"] >= 0.95
        verdict["verdict"] = "GO" if go else "NO-GO"
        print(
            f"\nH1 (OU2.5, walk-forward): n={len(h1)} | PSR {psr:.2f} | "
            f"IC95 pnl médio [{lo:+.4f}, {hi:+.4f}] | "
            f"DSR {dsr_info['dsr']:.2f} (N={dsr_info['n_trials']} tentativas, "
            f"SR0={dsr_info['sr0']:.4f})"
        )
        print(f"VEREDITO H1: {verdict['verdict']} (criterion: PSR>=0.80, IC_lower>0, DSR>=0.95)")
    else:
        verdict["verdict"] = "NO-GO"
        verdict["motivo"] = f"amostra insuficiente ({len(returns)} < 30 apostas)"
        print(f"\nH1: NO-GO — {verdict['motivo']}")
    summary["h1"] = verdict

    # ---- H2: acurácia dos picks de período ----
    h2 = {"n": len(h2_picks)}
    if h2_picks:
        hit = sum(p["won"] for p in h2_picks) / len(h2_picks)
        conf = st.mean(p["model_prob"] for p in h2_picks)
        h2.update({"hit": round(hit, 4), "conf_media": round(conf, 4), "validada": bool(hit >= H2_CONF)})
        print(
            f"\nH2 (picks 1T, prob≥{H2_CONF:.0%}): n={len(h2_picks)} | "
            f"acerto real {hit:.1%} vs confiança média {conf:.1%} → "
            f"{'VALIDADA (informativa)' if hit >= H2_CONF else 'NÃO validada'}"
        )
    else:
        print("\nH2: nenhum pick com confiança ≥ 60% (ou HT ausente na base)")
    summary["h2"] = h2

    # ---- persistência ----
    data = ROOT / "data"
    if ledger:
        with open(data / "backtest_bets_walkforward.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(ledger[0].keys()))
            w.writeheader()
            w.writerows(ledger)
    if h2_picks:
        with open(data / "period_picks_walkforward.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(h2_picks[0].keys()))
            w.writeheader()
            w.writerows(h2_picks)
    (data / "walkforward_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\nartefatos: backtest_bets_walkforward.csv, period_picks_walkforward.csv, walkforward_summary.json")


if __name__ == "__main__":
    main()
