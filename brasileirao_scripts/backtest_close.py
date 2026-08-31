"""Backtest walk-forward com TODAS as apostas a preço de FECHAMENTO.

Motivação (adendo 2026-07-17 do RELATORIO_BACKTEST): a auditoria da fonte
mostrou que o `initialFractionalValue` do Sofascore tem cara de
abertura-template (favorece OVER em ~64% das aberturas vs ~14% no
fechamento; 60% dos pares de abertura ficam mais perto do fechamento
INVERTIDO). Se a abertura é fictícia, o CLV open +19,55% e o ROI +7,9% da
H1 podem ser artefato. Este script é a tentativa de FALSIFICAÇÃO: refaz o
MESMO walk-forward (mesmos blocos, mesmo funil, mesmos jogos) forçando o
preço pactuado = fechamento — o único preço com evidência de ser real.

É diagnóstico read-only: não registra trial, não sobrescreve os artefatos
oficiais (backtest_bets_walkforward.csv etc.). NOTA: a preço de fechamento
o CLV é tautológico (~ -vig) — o juiz aqui é ROI/PSR/IC, não CLV.

Uso: python brasileirao_scripts/backtest_close.py
"""

import importlib.util
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.measurement.bootstrap import bootstrap_ci  # noqa: E402
from predictor_core.measurement.stats import probabilistic_sharpe_ratio  # noqa: E402

from brasileirao_predictor import backtest as bt_mod  # noqa: E402
from brasileirao_predictor import db  # noqa: E402
from brasileirao_predictor.ingest import load_config  # noqa: E402

spec = importlib.util.spec_from_file_location("backtest_walkforward", ROOT / "brasileirao_scripts" / "backtest_walkforward.py")
wf = importlib.util.module_from_spec(spec)
sys.modules["backtest_walkforward"] = wf
spec.loader.exec_module(wf)

_settle_orig = bt_mod._settle


def _settle_close(market, selection, p_model, p_shin_close, odd_open, odd_close, won, ctx, min_edge, max_edge):
    """Descarta a abertura: gatilho e P&L sempre no fechamento."""
    return _settle_orig(market, selection, p_model, p_shin_close, None, odd_close, won, ctx, min_edge, max_edge)


# patch nos DOIS namespaces: o walkforward importou o nome, e o
# _settle_extended resolve dentro de brasileirao_predictor.backtest
bt_mod._settle = _settle_close
wf._settle = _settle_close


def main():
    cfg = load_config()
    conn = db.connect(str(ROOT / cfg["database"]), read_only=True)
    ledger, _h2, n_blocks = wf.run_walkforward(cfg, conn)

    so = [b for b in ledger if b["bet_at"] != "close"]
    assert not so, f"{len(so)} apostas escaparam do preço de fechamento"

    print(
        f"\nWALK-FORWARD A FECHAMENTO — {n_blocks} blocos | "
        f"{len(ledger)} apostas no funil "
        f"[{cfg['backtest']['min_edge']:.0%}, {cfg['backtest']['max_edge']:.0%}]"
    )
    print("\npor mercado (preço = fechamento; CLV omitido por ser tautológico):")
    for mkt in sorted({b["market"] for b in ledger}):
        bets = [b for b in ledger if b["market"] == mkt]
        pnl = [b["pnl"] for b in bets]
        print(f"  {mkt:<12} n={len(bets):<5} acerto {st.mean(b['won'] for b in bets):.1%}  ROI {st.mean(pnl):+.1%}")

    h1 = [b for b in ledger if b["market"] == "ou25"]
    returns = [b["pnl"] for b in h1]
    print(f"\nPOPULAÇÃO H1 (OU2.5) A FECHAMENTO: n={len(h1)}")
    if len(returns) >= 30:
        psr = probabilistic_sharpe_ratio(returns, 0.0)
        lo, hi, _ = bootstrap_ci(
            h1,
            lambda bets: st.mean(b["pnl"] for b in bets),
            scheme="cluster",
            cluster_key=lambda b: (b["date"], b["home"], b["away"]),
            n_boot=int(cfg["backtest"].get("bootstrap_iterations", 1000)),
            seed=int(cfg["backtest"].get("bootstrap_seed", 13)),
        )
        sr = st.mean(returns) / st.stdev(returns) if st.stdev(returns) else 0.0
        print(f"  ROI {st.mean(returns):+.1%} | acerto {st.mean(b['won'] for b in h1):.1%} | sharpe/aposta {sr:.4f}")
        print(f"  PSR {psr:.2f} | IC95 pnl médio (cluster) [{lo:+.4f}, {hi:+.4f}]")
        edge_pos = lo is not None and lo > 0
        print(f"  -> edge a fechamento: {'POSITIVO com IC fechado' if edge_pos else 'NÃO demonstrado'}")
        print("\n  referência (backtest oficial, preço de ABERTURA): n=455, ROI +7,9%, PSR 0,94, IC95 [-0,022, +0,172]")
    else:
        print("  amostra insuficiente")

    print("\n(diagnóstico read-only — nenhum trial registrado, nenhum artefato oficial sobrescrito)")


if __name__ == "__main__":
    main()
