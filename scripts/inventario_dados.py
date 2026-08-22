"""Inventário da base — o que existe, por ano, por dimensão.

Somente-leitura (`mode=ro`, Regra P12). Conta LINHAS e preenchimento de campos;
não ajusta modelo, não avalia previsão, não lê desfecho para comparar com nada.

POR QUE ISSO NÃO QUEIMA O HOLDOUT: contar quantos jogos de 2025 têm odds é
metadado de cobertura. O que consome o holdout (Regra 7) é usá-lo para escolher
hiperparâmetro ou medir desempenho — nenhum dos dois acontece aqui. O ano
aparece na tabela como qualquer outro, de propósito: saber que a coleta está
íntegra é pré-requisito para o dia em que o selo for aberto.

Uso:
    python scripts/inventario_dados.py
    python scripts/inventario_dados.py --json     # machine-output
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB = ROOT / "data" / "matches.db"


def _configure_utf8_console() -> None:
    """Evita UnicodeEncodeError no console cp1252 do Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


# (rótulo, expressão SQL agregada sobre sofascore_matches)
DIMENSOES = [
    ("jogos", "COUNT(*)"),
    ("jogados", "SUM(home_score IS NOT NULL)"),
    ("kickoff", "SUM(kickoff_at IS NOT NULL)"),
    ("xG", "SUM(home_xg IS NOT NULL)"),
    ("1x2", "SUM(odds_home IS NOT NULL)"),
    ("1x2_open", "SUM(odds_home_open IS NOT NULL)"),
    ("ou25", "SUM(odds_over IS NOT NULL)"),
    ("ou25_open", "SUM(odds_over_open IS NOT NULL)"),
]


def _colunas(conn: sqlite3.Connection, tabela: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({tabela})")}


def _tabelas(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def coletar(conn: sqlite3.Connection) -> dict[str, Any]:
    existentes = _colunas(conn, "sofascore_matches")
    # Pula dimensão cuja coluna não existe nesta base: as odds de abertura e de
    # OU entraram por ALTER TABLE, então um clone antigo não as tem — e o
    # inventário tem que funcionar exatamente onde há dúvida sobre o que existe.
    dims = []
    for rot, sql in DIMENSOES:
        col = sql.split("(")[-1].split()[0].strip(")")
        if col in ("*",) or col in existentes:
            dims.append((rot, sql))

    select = ", ".join(sql for _, sql in dims)
    linhas = conn.execute(
        f"SELECT substr(date,1,4) ano, {select} FROM sofascore_matches GROUP BY 1 ORDER BY 1"
    ).fetchall()
    por_ano = [dict(zip(["ano"] + [r for r, _ in dims], linha)) for linha in linhas]

    tabelas = _tabelas(conn)
    extras: dict[str, Any] = {}

    # espelho `matches` — a tabela que o painel realmente lê
    extras["matches_por_ano"] = dict(
        conn.execute(
            "SELECT substr(date,1,4), COUNT(*) FROM matches WHERE home_score IS NOT NULL GROUP BY 1 ORDER BY 1"
        ).fetchall()
    )

    if "sofascore_player_ratings" in tabelas:
        extras["player_ratings_eventos"] = conn.execute(
            "SELECT COUNT(DISTINCT event_id) FROM sofascore_player_ratings"
        ).fetchone()[0]
    if "match_statistics" in tabelas:
        extras["match_statistics_eventos"] = conn.execute(
            "SELECT COUNT(DISTINCT event_id) FROM match_statistics"
        ).fetchone()[0]
    if "odds_snapshots" in tabelas:
        extras["odds_snapshots"] = [
            dict(zip(["market", "eventos", "fotos", "primeira", "ultima"], r))
            for r in conn.execute(
                "SELECT market, COUNT(DISTINCT event_id), COUNT(*), MIN(captured_at), MAX(captured_at) "
                "FROM odds_snapshots GROUP BY market"
            )
        ]
    if "player_comp_stats" in tabelas:
        extras["player_comp_stats"] = conn.execute("SELECT COUNT(*) FROM player_comp_stats").fetchone()[0]

    # Contradição conhecida: `src/db.py` documenta odds_*_open como NULL na base
    # histórica coletada pós-jogo ("abertura desconhecida != close"). Se a coluna
    # vier preenchida, ou a doc está velha ou a abertura veio de outro lugar —
    # e isso muda o que `market_no_vig` pode afirmar.
    if "odds_home_open" in existentes:
        r = conn.execute(
            "SELECT COUNT(*), SUM(odds_home <> odds_home_open) FROM sofascore_matches "
            "WHERE odds_home IS NOT NULL AND odds_home_open IS NOT NULL"
        ).fetchone()
        extras["abertura_vs_flat"] = {"pares": r[0], "diferentes": r[1]}

    return {"por_ano": por_ano, "dimensoes": [r for r, _ in dims], **extras}


def _tabela_texto(dados: dict[str, Any]) -> str:
    dims = dados["dimensoes"]
    largura = max(9, *(len(d) + 2 for d in dims))
    cab = "ano   " + "".join(d.rjust(largura) for d in dims)
    linhas = [cab, "-" * len(cab)]
    for linha in dados["por_ano"]:
        jogos = linha.get("jogos") or 0
        celulas = []
        for d in dims:
            v = linha.get(d) or 0
            if d in ("ano", "jogos"):
                celulas.append(str(v).rjust(largura))
            else:
                pct = (100 * v / jogos) if jogos else 0.0
                celulas.append(f"{v} ({pct:.0f}%)".rjust(largura))
        linhas.append(str(linha["ano"]).ljust(6) + "".join(celulas))
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_console()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="saída JSON em vez de tabela")
    args = parser.parse_args(argv)

    if not DB.exists():
        print(f"banco ausente: {DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        dados = coletar(conn)
    finally:
        conn.close()

    if args.json:
        print(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print("COBERTURA POR ANO — sofascore_matches (% sobre `jogos` do ano)\n")
    print(_tabela_texto(dados))
    print("\nESPELHO `matches` (jogos com placar, é o que o painel lê):")
    for ano, n in sorted(dados["matches_por_ano"].items()):
        print(f"  {ano}: {n}")
    for chave in ("player_ratings_eventos", "match_statistics_eventos", "player_comp_stats"):
        if chave in dados:
            print(f"\n{chave}: {dados[chave]}")
    if "odds_snapshots" in dados:
        print("\nodds_snapshots (série temporal prospectiva):")
        for s in dados["odds_snapshots"]:
            print(f"  {s['market']:6} eventos={s['eventos']:5} fotos={s['fotos']:6} {s['primeira']} → {s['ultima']}")
    if "abertura_vs_flat" in dados:
        a = dados["abertura_vs_flat"]
        pct = (100 * (a["diferentes"] or 0) / a["pares"]) if a["pares"] else 0
        print(f"\nabertura vs flat: {a['pares']} pares, {a['diferentes']} diferentes ({pct:.0f}%)")
        if pct < 20:
            print("  quase todas iguais => a coluna flat NÃO capturou movimento de linha:")
            print("  ela é abertura repetida, e NÃO serve como proxy de fechamento para market_no_vig")
        else:
            print("  a coluna flat capturou movimento de linha => serve como proxy de fechamento")
            print("  (é a última odd pré-jogo disponível, não a linha de fechamento de casa sharp)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
