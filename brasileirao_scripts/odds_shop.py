"""Descriptive bookmaker price comparison for Brasileirão.

The display validates complete prices and optional age limits. It does not
authenticate bookmaker availability, model calibration, costs or accepted fills.
Saved responses are locally received observations, not source publication clocks.
The legacy model comparison is diagnostic and cannot authorize capital.

Use --from-file for offline inspection. Network acquisition requires a separately
verified plan, quota and reserve; this legacy CLI does not establish that budget.
"""

import argparse
import json
import math
import os
import sqlite3
import ssl
import statistics
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from brasileirao_predictor import market_pricer as mp
from brasileirao_predictor.model import predict_match
from brasileirao_predictor.predict import _canon

ROOT = Path(__file__).resolve().parent.parent
API_BASE = "https://api.the-odds-api.com/v4"
# Importing this diagnostic must not read operational configuration.
SPORT = "soccer_brazil_campeonato"
MIN_EDGE_DEFAULT = 0.03
MIN_BOOKS = 4

_quota = {"remaining": None, "used": None}  # headers da última chamada


def _fetch(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "brasileirao-predictor"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        # quota do plano gratuito (500 req/mes): sem isto o operador descobre
        # que acabou na semana da final, quando mais precisa do line shopping
        _quota["remaining"] = r.headers.get("x-requests-remaining")
        _quota["used"] = r.headers.get("x-requests-used")
        return json.loads(r.read().decode("utf-8"))


def fetch_odds(api_key: str) -> list:
    params = urllib.parse.urlencode(
        {
            "apiKey": api_key,
            "regions": "eu,uk,us",
            "markets": "h2h,totals",
            "oddsFormat": "decimal",
        }
    )
    data = _fetch(f"{API_BASE}/sports/{SPORT}/odds?{params}")
    if not isinstance(data, list):
        raise ValueError("expected_event_list")
    # Snapshot local recebido; published_at da fonte permanece desconhecido.
    out_dir = ROOT / "data" / "odds_shop"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    with (out_dir / f"odds_{stamp}_{uuid4().hex}.json").open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(data, allow_nan=False))
    return data


def devig_probs(prices: list[float]) -> list[float]:
    """Normalizacao proporcional das implicitas de UMA casa (rapido e adequado
    para consenso; o Shin fica para o pipeline principal)."""
    if len(prices) < 2 or any(type(p) not in (int, float) or not math.isfinite(p) or p <= 1 for p in prices):
        raise ValueError("complete_finite_decimal_prices_required")
    imp = [1.0 / p for p in prices]
    s = sum(imp)
    return [x / s for x in imp]


def _stale(bk: dict, max_stale_s: float | None) -> bool:
    """Unknown, invalid and future clocks cannot establish online freshness.

    None disables the age filter only for retrospective display.
    """
    if max_stale_s is None:
        return False
    if not math.isfinite(max_stale_s) or max_stale_s <= 0:
        raise ValueError("positive_finite_age_limit_required")
    lu = bk.get("last_update")
    if not lu:
        return True
    try:
        instant = datetime.fromisoformat(lu.replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            return True
        age = (datetime.now(UTC) - instant).total_seconds()
    except (TypeError, ValueError, AttributeError, OverflowError):
        return True
    return not 0 <= age <= max_stale_s


def consensus(event: dict, market_key: str, point=None, max_stale_s: float | None = None) -> dict:
    """{selecao: {'best': (odd, casa), 'consensus_prob': float, 'n_books': int}}
    Medianas renormalizadas, com mercados completos e casas distintas.
    Estatística descritiva; não prova aceitação da oferta nem vantagem econômica.
    """
    per_book: dict = {}
    expected = {event.get("home_team"), "Draw", event.get("away_team")} if market_key == "h2h" else {"Over", "Under"}
    if None in expected or (market_key == "h2h" and len(expected) != 3):
        return {}
    books = [bk for bk in event.get("bookmakers", []) if isinstance(bk, dict) and isinstance(bk.get("key"), str)]
    counts = Counter(bk["key"] for bk in books)
    for bk in books:
        if not bk["key"].strip() or counts[bk["key"]] != 1:
            continue
        if _stale(bk, max_stale_s):
            continue
        candidates = []
        for m in bk.get("markets", []):
            if not isinstance(m, dict) or m.get("key") != market_key:
                continue
            outs = m.get("outcomes", [])
            if not isinstance(outs, list) or any(not isinstance(o, dict) for o in outs):
                continue
            if point is not None:
                outs = [o for o in outs if o.get("point") == point]
            if not outs:
                continue
            candidates.append((m, outs))
        if len(candidates) != 1:
            continue
        market, outs = candidates[0]
        if "last_update" in market and _stale(market, max_stale_s):
            continue
        if len(outs) != len(expected) or {o.get("name") for o in outs} != expected:
            continue
        try:
            probs = devig_probs([o["price"] for o in outs])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        for o, p in zip(outs, probs):
            per_book.setdefault(o["name"], []).append((o["price"], bk.get("title") or bk["key"], p))
    out = {}
    for name, entries in per_book.items():
        best = max(entries, key=lambda e: e[0])
        out[name] = {
            "best": (best[0], best[1]),
            "consensus_prob": statistics.median(e[2] for e in entries),
            "n_books": len(entries),
        }
    total = sum(item["consensus_prob"] for item in out.values())
    for item in out.values():
        item["consensus_prob"] /= total
    return out


def model_probs_for(home: str, away: str):
    """Probabilidades do modelo (campo neutro) ou None se times desconhecidos."""
    conn = sqlite3.connect(f"file:{ROOT / 'data' / 'matches.db'}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    elo = {t: e for t, e in conn.execute("SELECT team, elo FROM current_elo")}
    prow = conn.execute("SELECT param_a, param_b, param_alpha, param_rho FROM model_parameters WHERE id=1").fetchone()
    conn.close()
    canon_elo = {_canon(t): e for t, e in elo.items()}
    eh, ea = canon_elo.get(_canon(home)), canon_elo.get(_canon(away))
    if eh is None or ea is None or not prow:
        return None
    r = predict_match(eh, ea, tuple(prow))
    ou = mp.over_under(r["grid"], 2.5)
    return {
        "home": r["p_win"],
        "draw": r["p_draw"],
        "away": r["p_loss"],
        "over25": ou["Over"],
        "under25": ou["Under"],
    }


def period_probs_for(home: str, away: str) -> dict[str, Any] | None:
    """P(over linha) do MODELO por período (1T/2T), com a fração calibrada no
    placar de intervalo ingerido (display.ht_goal_fraction). None se times
    desconhecidos ou sem calibração — mercado de tempo SEM modelo é só preço."""
    from brasileirao_predictor.display import ht_goal_fraction
    from brasileirao_predictor.model import _score_grid

    conn = sqlite3.connect(f"file:{ROOT / 'data' / 'matches.db'}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    elo = {t: e for t, e in conn.execute("SELECT team, elo FROM current_elo")}
    prow = conn.execute("SELECT param_a, param_b, param_alpha, param_rho FROM model_parameters WHERE id=1").fetchone()
    calib = ht_goal_fraction(conn)
    conn.close()
    canon_elo = {_canon(t): e for t, e in elo.items()}
    eh, ea = canon_elo.get(_canon(home)), canon_elo.get(_canon(away))
    if eh is None or ea is None or not prow or calib is None:
        return None
    a, b, alpha, rho = prow
    import math

    import numpy as np

    diff = (eh - ea) / 400.0
    lam_a, lam_b = math.exp(a + b * diff), math.exp(a - b * diff)
    out: dict[str, Any] = {"calib_n": calib["n"]}
    for tag, fr in (("1T", calib["frac1"]), ("2T", 1.0 - calib["frac1"])):
        g = _score_grid(lam_a * fr, lam_b * fr, alpha, rho, 12)
        k = np.arange(g.shape[0])
        tot = k.reshape(-1, 1) + k.reshape(1, -1)
        out[tag] = {ln: float(g[tot > ln].sum()) for ln in (0.5, 1.5, 2.5)}
    return out


def fetch_period_odds(api_key: str, event_id: str) -> dict | None:
    """Mercados de tempo (totals_h1/h2) — só existem no endpoint POR EVENTO da
    The Odds API (o bulk /odds não os serve). Custo de quota: mercados×regiões
    por chamada. None em erro (jogo sem esses mercados ainda, plano, etc.)."""
    params = urllib.parse.urlencode(
        {
            "apiKey": api_key,
            "regions": "eu,uk,us",
            "markets": "totals_h1,totals_h2",
            "oddsFormat": "decimal",
        }
    )
    try:
        data = _fetch(f"{API_BASE}/sports/{SPORT}/events/{event_id}/odds?{params}")
        if not isinstance(data, dict):
            raise ValueError("expected_event_object")
    except Exception:
        print("  (mercados de tempo indisponiveis: falha da fonte)")
        return None
    out_dir = ROOT / "data" / "odds_shop"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    with (out_dir / f"odds_h1h2_{stamp}_{uuid4().hex}.json").open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(data, allow_nan=False))
    return data


def _verdict(selection_kind: str, p_model, p_cons, best_odd, n_books, min_edge) -> str:
    """Display a descriptive discrepancy without granting economic approval."""
    imp_best = 1.0 / best_odd
    if n_books < MIN_BOOKS:
        return "poucas casas — so informativo"
    # valor "de graca": melhor preco acima do consenso de-vigado
    edge_cons = p_cons - imp_best
    notes = []
    if edge_cons >= min_edge:
        notes.append(f"diferenca vs consenso {edge_cons:+.1%} (diagnostico)")
    if p_model is not None:
        edge_model = p_model - imp_best
        if edge_model >= min_edge:
            notes.append(f"diferenca vs modelo {edge_model:+.1%} (diagnostico)")
    return " | ".join(notes) if notes else ""


def _started(ev: dict) -> bool:
    """Jogo ja iniciado: odds sao AO VIVO — comparar com modelo pre-jogo gera
    'valor' fantasma (ex.: empate a 126 com o favorito vencendo em campo)."""
    ct = ev.get("commence_time")
    if not ct:
        return True
    try:
        start = datetime.fromisoformat(ct.replace("Z", "+00:00"))
        if start.tzinfo is None or start.utcoffset() is None:
            return True
        return start <= datetime.now(UTC)
    except (TypeError, ValueError, AttributeError, OverflowError):
        return True


def analyze(
    events: list,
    jogo_filter: str | None,
    min_edge: float,
    tempos_key: str | None = None,
    max_stale_s: float | None = None,
) -> None:
    for ev in events:
        home, away = ev.get("home_team", "?"), ev.get("away_team", "?")
        if jogo_filter and jogo_filter.lower() not in f"{home} {away}".lower():
            continue
        if _started(ev):
            print(f"\n{home} x {away}: inicio futuro nao confirmado; comparacao pre-jogo omitida.")
            continue
        print(f"\n{'=' * 66}\n{home} x {away}  ({ev.get('commence_time', '?')})\n{'=' * 66}")
        pm = model_probs_for(home, away)
        if pm is None:
            print("  (times fora do Elo local — sem cruzamento com o modelo)")

        h2h = consensus(ev, "h2h", max_stale_s=max_stale_s)
        if h2h:
            print(f"  {'1X2':<12}{'melhor odd':>11}  {'casa':<18}{'consenso':>9}{'modelo':>8}  veredito")
            fav_prob = max((d["consensus_prob"] for d in h2h.values()), default=0)
            for name, d in sorted(h2h.items(), key=lambda kv: -kv[1]["consensus_prob"]):
                if name == "Draw":
                    kind, p_mod = "draw", pm and pm["draw"]
                elif d["consensus_prob"] >= fav_prob - 1e-9:
                    kind, p_mod = "favorite", pm and (pm["home"] if name == home else pm["away"])
                else:
                    kind, p_mod = "underdog", pm and (pm["home"] if name == home else pm["away"])
                v = _verdict(kind, p_mod, d["consensus_prob"], d["best"][0], d["n_books"], min_edge)
                label = "Empate" if name == "Draw" else name
                print(
                    f"  {label[:12]:<12}{d['best'][0]:>11.2f}  {d['best'][1][:18]:<18}"
                    f"{d['consensus_prob']:>9.1%}"
                    f"{(f'{p_mod:.1%}' if p_mod is not None else '—'):>8}  {v}"
                )

        tot = consensus(ev, "totals", point=2.5, max_stale_s=max_stale_s)
        if tot:
            print(f"  {'Gols 2.5':<12}{'melhor odd':>11}  {'casa':<18}{'consenso':>9}{'modelo':>8}  veredito")
            for name, d in tot.items():
                p_mod = pm and (pm["over25"] if name == "Over" else pm["under25"])
                v = _verdict("total", p_mod, d["consensus_prob"], d["best"][0], d["n_books"], min_edge)
                print(
                    f"  {name:<12}{d['best'][0]:>11.2f}  {d['best'][1][:18]:<18}"
                    f"{d['consensus_prob']:>9.1%}"
                    f"{(f'{p_mod:.1%}' if p_mod is not None else '—'):>8}  {v}"
                )
        if tempos_key:
            _analyze_periods(ev, home, away, tempos_key, max_stale_s=max_stale_s)


_PERIOD_MARKETS = (("totals_h1", "1T"), ("totals_h2", "2T"))
_PERIOD_LINES = (0.5, 1.5, 2.5)


def _analyze_periods(ev: dict, home: str, away: str, api_key: str, max_stale_s: float | None = None) -> None:
    """Display period-price diagnostics without a betting recommendation."""
    data = fetch_period_odds(api_key, ev.get("id", ""))
    if not data:
        return
    pp = period_probs_for(home, away)
    for mkey, tag in _PERIOD_MARKETS:
        blocks = []
        for ln in _PERIOD_LINES:
            c = consensus(data, mkey, point=ln, max_stale_s=max_stale_s)
            if c:
                blocks.append((ln, c))
        if not blocks:
            continue
        print(f"  {'Gols ' + tag:<12}{'melhor odd':>11}  {'casa':<18}{'consenso':>9}{'modelo':>8}  [SEM CLV validado]")
        for ln, c in blocks:
            for name, d in c.items():
                p_over = pp[tag].get(ln) if pp is not None else None
                p_mod = None if p_over is None else (p_over if name == "Over" else 1.0 - p_over)
                marker = ""
                if p_mod is not None:
                    edge_best = p_mod - 1.0 / d["best"][0]
                    if p_mod >= 0.60 and edge_best > 0:
                        marker = f"diferenca vs modelo {edge_best:+.1%} (diagnostico)"
                print(
                    f"  {name + ' ' + str(ln):<12}{d['best'][0]:>11.2f}  "
                    f"{d['best'][1][:18]:<18}{d['consensus_prob']:>9.1%}"
                    f"{(f'{p_mod:.1%}' if p_mod is not None else '—'):>8}  {marker}"
                )


def _footer(min_edge: float) -> None:
    print(f"\nLimiar de exibicao das diferencas: {min_edge:.0%}.")
    print("Comparacao descritiva: custos, aceitacao e lucro executavel nao foram validados.")
    print("Capital permanece desabilitado; probabilidades do cache legado sao diagnosticas.")
    if _quota["remaining"] is not None:
        print(f"Quota The Odds API: {_quota['remaining']} requests restantes ({_quota['used']} usadas no ciclo).")


def main() -> int:
    global SPORT
    ap = argparse.ArgumentParser(description="Line shopping multi-casas + cruzamento com o modelo")
    ap.add_argument("--jogo", help="filtra por nome de time (substring)")
    ap.add_argument("--min-edge", type=float, default=MIN_EDGE_DEFAULT)
    ap.add_argument("--from-file", help="JSON salvo da API (offline/teste)")
    ap.add_argument(
        "--tempos",
        action="store_true",
        help="inclui odds de 1o/2o tempo (totals_h1/h2 — 1 chamada de API POR JOGO; use com --jogo pra poupar quota)",
    )
    ap.add_argument(
        "--max-stale-min",
        type=float,
        default=15.0,
        help="descarta casa cujo last_update tem mais que N minutos "
        "(W5: feed congelado vira melhor preco fantasma). "
        "Exige valor positivo no modo online; --from-file nunca "
        "filtra (snapshot e' velho por definicao). Default: 15",
    )
    args = ap.parse_args()
    if not math.isfinite(args.min_edge) or not 0 <= args.min_edge <= 1:
        ap.error("--min-edge deve estar entre 0 e 1")
    if not args.from_file and (not math.isfinite(args.max_stale_min) or args.max_stale_min <= 0):
        ap.error("--max-stale-min deve ser finito e positivo")
    if args.from_file and args.tempos:
        ap.error("--from-file nao permite consultas de rede com --tempos")

    max_stale_s = None
    if args.from_file:
        events = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
    else:
        from brasileirao_predictor.ingest import load_config

        sport = (load_config().get("odds_shop") or {}).get("sport", SPORT)
        if not isinstance(sport, str) or not sport.startswith("soccer_") or not sport.replace("_", "").isalnum():
            ap.error("sport key invalida")
        SPORT = sport
        if args.max_stale_min > 0:
            max_stale_s = args.max_stale_min * 60.0
        key = os.environ.get("ODDS_API_KEY")
        if not key:
            print(
                "ODDS_API_KEY nao definida.\n"
                "  1. Chave gratis: https://the-odds-api.com (500 req/mes)\n"
                '  2. PowerShell:  $env:ODDS_API_KEY = "sua_chave"\n'
                "  3. Confira plano, quota e reservas antes de qualquer coleta."
            )
            return 2
        try:
            events = fetch_odds(key)
        except Exception:
            print("falha na API de odds: fonte indisponivel")
            return 1

    if not events:
        print("nenhum jogo com odds no momento.")
        return 0
    tempos_key = os.environ.get("ODDS_API_KEY") if args.tempos else None
    if args.tempos and not tempos_key:
        print("[--tempos ignorado: ODDS_API_KEY nao definida — mercados de tempo exigem o endpoint por evento]")
    analyze(events, args.jogo, args.min_edge, tempos_key=tempos_key, max_stale_s=max_stale_s)
    _footer(args.min_edge)
    return 0


if __name__ == "__main__":
    sys.exit(main())
