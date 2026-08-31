"""Inventário da base — cobertura por ano.

Testa o inventário contra uma base montada com o DDL REAL de `brasileirao_predictor.db`: um
inventário que mente sobre o que existe é pior que nenhum, porque decisões de
roadmap penduram nele (o `market_no_vig` depende da cobertura de odds).
"""

from __future__ import annotations

import ast
import pathlib
import re
import sqlite3
import tempfile

import pytest

from brasileirao_scripts import inventario_dados as inv
from brasileirao_predictor import db


def _base(monkeypatch, com_open: bool = True, open_igual: bool = False) -> pathlib.Path:
    path = pathlib.Path(tempfile.mkdtemp()) / "m.db"
    conn = db.connect(str(path))
    for i, (ano, n) in enumerate([("2021", 6), ("2025", 4)]):
        for j in range(n):
            d = f"{ano}-05-{j + 1:02d}"
            eid = i * 100 + j
            conn.execute(
                "INSERT INTO matches (date, home_team, away_team, home_score, away_score, tournament, neutral)"
                " VALUES (?,?,?,?,?,?,0)",
                (d, f"A{j}", f"B{j}", 1, 0, "Brasileirão Série A"),
            )
            flat = 2.1
            abertura = flat if open_igual else 2.0
            conn.execute(
                "INSERT INTO sofascore_matches (event_id, date, kickoff_at, home_team, away_team,"
                " home_score, away_score, home_xg, odds_home, odds_home_open)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    eid,
                    d,
                    d + "T20:00:00+00:00",
                    f"A{j}",
                    f"B{j}",
                    1,
                    0,
                    1.2 if j % 2 == 0 else None,
                    flat,
                    abertura if com_open else None,
                ),
            )
    conn.commit()
    conn.close()
    monkeypatch.setattr(inv, "DB", path)
    return path


def test_conta_jogos_e_cobertura_por_ano(monkeypatch) -> None:
    _base(monkeypatch)
    conn = sqlite3.connect(f"file:{inv.DB}?mode=ro", uri=True)
    dados = inv.coletar(conn)
    conn.close()

    por_ano = {linha["ano"]: linha for linha in dados["por_ano"]}
    assert por_ano["2021"]["jogos"] == 6
    assert por_ano["2025"]["jogos"] == 4
    # xG só nos índices pares: 3 de 6 em 2021, 2 de 4 em 2025
    assert por_ano["2021"]["xG"] == 3
    assert por_ano["2025"]["xG"] == 2
    assert por_ano["2021"]["1x2"] == 6


def test_espelho_matches_entra_separado(monkeypatch) -> None:
    """`matches` é a tabela que o painel lê; divergir de `sofascore_matches` é
    exatamente o tipo de coisa que o inventário existe para expor."""
    _base(monkeypatch)
    conn = sqlite3.connect(f"file:{inv.DB}?mode=ro", uri=True)
    dados = inv.coletar(conn)
    conn.close()
    assert dados["matches_por_ano"]["2021"] == 6


def test_detecta_abertura_identica_ao_flat(monkeypatch) -> None:
    """Se abertura == flat em tudo, a coluna flat não tem movimento de linha e
    não serve de proxy de fechamento — a diferença decide se o `market_no_vig`
    mede o teto ou uma versão fraca dele."""
    _base(monkeypatch, open_igual=True)
    conn = sqlite3.connect(f"file:{inv.DB}?mode=ro", uri=True)
    dados = inv.coletar(conn)
    conn.close()
    assert dados["abertura_vs_flat"]["pares"] == 10
    assert dados["abertura_vs_flat"]["diferentes"] == 0


def test_detecta_movimento_de_linha(monkeypatch) -> None:
    _base(monkeypatch, open_igual=False)
    conn = sqlite3.connect(f"file:{inv.DB}?mode=ro", uri=True)
    dados = inv.coletar(conn)
    conn.close()
    assert dados["abertura_vs_flat"]["diferentes"] == 10


def test_somente_leitura() -> None:
    """Regra P12: pesquisa não abre o banco em modo escrita.

    Verifica o que importa — que TODA query executada seja SELECT ou PRAGMA —
    em vez de procurar a palavra 'INSERT' no arquivo, que casaria com
    `sys.path.insert` e daria falso positivo."""
    fonte = pathlib.Path(inv.__file__).read_text(encoding="utf-8")
    assert "mode=ro" in fonte, "conexão sem mode=ro"

    arvore = ast.parse(fonte)
    queries = [
        no.args[0].value
        for no in ast.walk(arvore)
        if isinstance(no, ast.Call)
        and isinstance(no.func, ast.Attribute)
        and no.func.attr == "execute"
        and no.args
        and isinstance(no.args[0], ast.Constant)
        and isinstance(no.args[0].value, str)
    ]
    assert queries, "nenhuma query encontrada — o teste deixou de exercitar algo"
    for q in queries:
        primeira = q.strip().split()[0].upper()
        assert primeira in {"SELECT", "PRAGMA"}, f"query de escrita no inventário: {q[:60]}"


def test_queries_f_string_tambem_sao_leitura() -> None:
    """As duas queries montadas por f-string (colunas dinâmicas) escapam da
    checagem por AST acima; confere o prefixo delas no texto."""
    fonte = pathlib.Path(inv.__file__).read_text(encoding="utf-8")
    for trecho in re.findall(r'f"(SELECT[^"]*|PRAGMA[^"]*)"', fonte):
        assert trecho.split()[0].upper() in {"SELECT", "PRAGMA"}
    assert 'f"PRAGMA table_info' in fonte or "PRAGMA table_info" in fonte


def test_banco_ausente_falha_limpo(monkeypatch, capsys) -> None:
    monkeypatch.setattr(inv, "DB", pathlib.Path(tempfile.mkdtemp()) / "nao_existe.db")
    assert inv.main([]) == 1
    assert "banco ausente" in capsys.readouterr().err


def test_saida_json(monkeypatch, capsys) -> None:
    import json

    _base(monkeypatch)
    assert inv.main(["--json"]) == 0
    dados = json.loads(capsys.readouterr().out)
    assert {"por_ano", "dimensoes", "matches_por_ano"} <= set(dados)


@pytest.mark.parametrize("ano", ["2021", "2025"])
def test_ano_do_holdout_aparece_como_qualquer_outro(monkeypatch, ano: str) -> None:
    """Contar cobertura não é medir modelo. 2025 entra na tabela de propósito:
    saber que a coleta está íntegra é pré-requisito para o dia em que o selo
    for aberto — e omiti-lo esconderia uma falha de coleta até tarde demais."""
    _base(monkeypatch)
    conn = sqlite3.connect(f"file:{inv.DB}?mode=ro", uri=True)
    dados = inv.coletar(conn)
    conn.close()
    assert any(linha["ano"] == ano for linha in dados["por_ano"])
