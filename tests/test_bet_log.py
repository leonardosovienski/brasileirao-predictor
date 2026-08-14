"""Livro-caixa de apostas: registro, settle com lucro/push e ROI acumulado.
Tudo em tmp_path — nunca toca data/bets.jsonl real."""

import json

import pytest

from src.bet_log import (
    add_bet,
    bank_flow,
    bank_init,
    bank_state,
    capital_gate_status,
    list_bets,
    settle_bet,
    summary,
)


def test_add_grava_linha_aberta(tmp_path):
    p = tmp_path / "bets.jsonl"
    rec = add_bet(
        "Norway",
        "England",
        "ou25",
        "under",
        2.21,
        book="BetOnline",
        edge=0.095,
        model_prob=0.548,
        match_date="2026-07-11",
        path=p,
    )
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    r = json.loads(lines[0])
    assert r["kind"] == "bet" and r["status"] == "open"
    assert r["selection"] == "under" and r["line"] == 2.5 and r["odds"] == 2.21
    assert r["stake"] == 1.0  # stake fixo default
    assert rec["book"] == "BetOnline"


def test_add_rejeita_mercado_e_odd_invalidos(tmp_path):
    p = tmp_path / "bets.jsonl"
    with pytest.raises(ValueError):
        add_bet("A", "B", "1x2", "home", 2.0, path=p)  # mercado sem CLV
    with pytest.raises(ValueError):
        add_bet("A", "B", "ou25", "over", 0.9, path=p)  # odd <= 1
    with pytest.raises(ValueError):
        add_bet("A", "B", "ou25", "over", 2.0, stake=-3, path=p)  # stake < 0
    with pytest.raises(ValueError):
        add_bet("A", "B", "ou25", "over", 2.0, stake=0, path=p)  # stake = 0


def test_settle_rejeita_placar_negativo(tmp_path):
    p = tmp_path / "bets.jsonl"
    add_bet("A", "B", "ou25", "over", 2.0, path=p)
    with pytest.raises(ValueError):
        settle_bet("A", "B", -1, 0, path=p)
    with pytest.raises(ValueError):
        settle_bet("A", "B", 2, 1, ht="0--1", path=p)  # HT negativo via parse


def test_settle_ganha_perde_e_nao_duplica(tmp_path):
    p = tmp_path / "bets.jsonl"
    add_bet("Norway", "England", "ou25", "under", 2.21, path=p)
    add_bet("Norway", "England", "ou25", "over", 2.30, path=p)
    recs = settle_bet("Norway", "England", 0, 1, path=p)  # total 1 -> under ganha
    assert len(recs) == 2
    by_sel = {r["selection"]: r for r in recs}
    assert by_sel["under"]["won"] is True
    assert by_sel["under"]["profit"] == pytest.approx(1.21)
    assert by_sel["over"]["won"] is False
    assert by_sel["over"]["profit"] == -1.0
    # settle repetido nao re-fecha (append-only, idempotente)
    assert settle_bet("Norway", "England", 0, 1, path=p) == []


def test_settle_casa_por_conjunto_de_times(tmp_path):
    # resultado informado na ordem invertida ainda fecha a aposta
    p = tmp_path / "bets.jsonl"
    add_bet("Norway", "England", "ou25", "under", 2.0, path=p)
    recs = settle_bet("England", "Norway", 3, 1, path=p)  # total 4 -> under perde
    assert len(recs) == 1 and recs[0]["won"] is False


def test_settle_periodo_exige_ht_e_fecha_com_ht(tmp_path):
    # 1T/2T: sem --ht a aposta de período segue aberta; com HT fecha certo.
    p = tmp_path / "bets.jsonl"
    add_bet("A", "B", "ou05_1t", "over", 2.4, path=p)  # >=1 gol no 1o tempo
    add_bet("A", "B", "ou15_2t", "under", 1.8, path=p)  # <2 gols no 2o tempo
    add_bet("A", "B", "ou25", "under", 2.0, path=p)  # jogo inteiro
    recs = settle_bet("A", "B", 2, 1, path=p)  # sem ht
    assert [r["market"] for r in recs] == ["ou25"]  # só o FT fechou
    recs = settle_bet("A", "B", 2, 1, ht="0-1", path=p)  # 1T=1 gol, 2T=2 gols
    by = {r["market"]: r for r in recs}
    assert by["ou05_1t"]["won"] is True  # 1 > 0.5
    assert by["ou15_2t"]["won"] is False  # 2 > 1.5 -> under perde
    assert by["ou05_1t"]["validated"] is False  # marcado sem CLV
    # nada re-fecha
    assert settle_bet("A", "B", 2, 1, ht="0-1", path=p) == []


def test_summary_separa_validado_de_informativo(tmp_path):
    p = tmp_path / "bets.jsonl"
    add_bet("A", "B", "ou25", "under", 2.0, path=p)
    add_bet("A", "B", "ou05_1t", "over", 2.0, path=p)
    settle_bet("A", "B", 1, 0, ht="1-0", path=p)
    t = summary(path=p)
    assert t["ou25"]["validated"] is True
    assert t["ou05_1t"]["validated"] is False


def test_summary_roi(tmp_path):
    p = tmp_path / "bets.jsonl"
    add_bet("A1", "B1", "ou25", "under", 2.0, path=p)
    add_bet("A2", "B2", "ou25", "over", 2.0, path=p)
    settle_bet("A1", "B1", 1, 0, path=p)  # under ganha: +1.0
    settle_bet("A2", "B2", 1, 0, path=p)  # over perde: -1.0
    t = summary(path=p)["ou25"]
    assert t["n"] == 2 and t["staked"] == 2.0
    assert t["profit"] == pytest.approx(0.0)
    assert t["roi"] == pytest.approx(0.0)


def test_banca_saldo_exposicao_e_drawdown(tmp_path):
    bank = tmp_path / "bankroll.jsonl"
    bets = tmp_path / "bets.jsonl"
    bank_init(1000.0, 20.0, path=bank)  # unidade = 2% da banca
    add_bet("A1", "B1", "ou25", "under", 2.0, path=bets)
    add_bet("A2", "B2", "ou25", "over", 2.5, path=bets)
    st = bank_state(bank_path=bank, bets_path=bets)
    assert st["balance"] == 1000.0  # nada fechado ainda
    assert st["open_units"] == 2.0 and st["open_money"] == 40.0
    settle_bet("A1", "B1", 3, 1, path=bets)  # under 2.5 perde: -1u
    settle_bet("A2", "B2", 2, 1, path=bets)  # over 2.5 ganha: +1.5u
    st = bank_state(bank_path=bank, bets_path=bets)
    assert st["profit_units"] == pytest.approx(0.5)
    assert st["balance"] == pytest.approx(1000.0 + 0.5 * 20.0)
    assert st["open_units"] == 0.0
    # drawdown: perdeu 1u (20) antes de ganhar — pico 1000, vale 980
    assert st["max_drawdown_money"] == pytest.approx(20.0)


def test_banca_deposito_saque_e_reinit(tmp_path):
    bank = tmp_path / "bankroll.jsonl"
    bets = tmp_path / "bets.jsonl"
    bank_init(500.0, 10.0, path=bank)
    bank_flow("deposit", 200.0, path=bank)
    bank_flow("withdraw", 100.0, path=bank)
    st = bank_state(bank_path=bank, bets_path=bets)
    assert st["balance"] == 600.0 and st["flows"] == 100.0
    bank_init(1000.0, 20.0, path=bank)  # reinit zera fluxos
    st = bank_state(bank_path=bank, bets_path=bets)
    assert st["balance"] == 1000.0 and st["flows"] == 0.0


def test_kickoff_marca_aposta_tardia(tmp_path):
    # dinheiro real: aposta registrada APÓS o apito não tem edge pré-jogo —
    # fica carimbada late=True (o registro entra, mas marcado).
    p = tmp_path / "bets.jsonl"
    cedo = add_bet(
        "A",
        "B",
        "ou25",
        "under",
        2.0,
        path=p,
        kickoff="2026-07-09T20:00:00Z",
        logged_at="2026-07-09T18:00:00+00:00",
    )
    tarde = add_bet(
        "A",
        "B",
        "ou25",
        "over",
        2.0,
        path=p,
        kickoff="2026-07-09T20:00:00Z",
        logged_at="2026-07-09T20:05:00+00:00",
    )
    assert cedo["late"] is False
    assert tarde["late"] is True
    sem_ko = add_bet("A", "B", "ou15", "over", 2.0, path=p)
    assert sem_ko["late"] is None  # sem kickoff, sem juízo


def test_aviso_de_bilhete_duplicado_aberto(tmp_path):
    p = tmp_path / "bets.jsonl"
    a = add_bet("A", "B", "ou25", "under", 2.0, path=p)
    b = add_bet("B", "A", "ou25", "under", 2.1, path=p)  # mesmo jogo invertido
    assert a["duplicate_of_open"] is False
    assert b["duplicate_of_open"] is True
    settle_bet("A", "B", 1, 0, path=p)  # fecha as duas
    c = add_bet("A", "B", "ou25", "under", 2.0, path=p)  # não há mais aberta
    assert c["duplicate_of_open"] is False


def test_settle_rejeita_ht_maior_que_final(tmp_path):
    p = tmp_path / "bets.jsonl"
    add_bet("A", "B", "ou05_1t", "over", 2.0, path=p)
    with pytest.raises(ValueError):
        settle_bet("A", "B", 1, 0, ht="2-1", path=p)  # 3 gols no HT, 1 no FT


def test_list_bets_casa_aberta_e_fechada(tmp_path):
    p = tmp_path / "bets.jsonl"
    add_bet("A", "B", "ou25", "under", 2.0, path=p)
    add_bet("C", "D", "ou25", "over", 2.0, path=p)
    settle_bet("A", "B", 1, 0, path=p)
    rows = list_bets(path=p)
    by = {(r["home"], r["away"]): r for r in rows}
    assert by[("A", "B")]["result"] is not None  # fechada
    assert by[("A", "B")]["result"]["won"] is True
    assert by[("C", "D")]["result"] is None  # aberta


def test_banca_none_sem_init(tmp_path):
    assert bank_state(bank_path=tmp_path / "nada.jsonl", bets_path=tmp_path / "bets.jsonl") is None
    with pytest.raises(ValueError):
        bank_init(-5, 1, path=tmp_path / "bankroll.jsonl")
    with pytest.raises(ValueError):
        bank_flow("roubo", 10, path=tmp_path / "bankroll.jsonl")


# ---------------- auditoria hostil 2026-07-17: bugs CRÍTICOS de settlement ----------------


def test_settle_confronto_repetido_exige_match_date_para_desambiguar(tmp_path):
    # Regressão: turno (2026-05-01) e returno (2026-06-01) do mesmo par de
    # times eram liquidados JUNTOS com o mesmo placar quando settle_bet só
    # casava por frozenset(casa,fora) — a aposta do returno (ainda não
    # jogado) era fechada com o placar do turno. Agora, com 2 datas abertas
    # e sem match_date, a função recusa em vez de adivinhar.
    p = tmp_path / "bets.jsonl"
    add_bet("Flamengo", "Vasco", "ou25", "over", 2.0, match_date="2026-05-01", path=p)
    add_bet("Vasco", "Flamengo", "ou25", "under", 2.0, match_date="2026-06-01", path=p)
    with pytest.raises(ValueError, match="datas diferentes"):
        settle_bet("Flamengo", "Vasco", 3, 1, path=p)
    # com match_date, liquida SÓ o jogo daquela data
    recs = settle_bet("Flamengo", "Vasco", 3, 1, match_date="2026-05-01", path=p)
    assert len(recs) == 1
    assert recs[0]["won"] is True  # over 2.5 bateu (3+1=4)
    ainda_abertas = [b for b in list_bets(path=p) if b["result"] is None]
    assert len(ainda_abertas) == 1
    assert ainda_abertas[0]["match_date"] == "2026-06-01"  # returno intocado


def test_settle_idempotente_sobrevive_a_reordenacao_do_arquivo(tmp_path):
    # Regressão: settled_ids era chaveado por bet_line_no (índice posicional).
    # Se o arquivo fosse reescrito com uma linha nova inserida ANTES das
    # existentes, o índice da aposta original mudava e a checagem de
    # duplicata não batia mais — settle_bet pagava a MESMA aposta 2x.
    # Com dedup por bet_id (estável), isso não acontece mais.
    p = tmp_path / "bets.jsonl"
    rec = add_bet("A", "B", "ou25", "over", 2.0, bet_id="fixed-id-1", path=p)
    settle_bet("A", "B", 3, 1, path=p)
    original_lines = p.read_text(encoding="utf-8").splitlines()
    # simula reescrita concorrente: insere uma linha nova ANTES das existentes
    nova_linha = json.dumps({**rec, "bet_id": "outra-aposta", "home": "X", "away": "Y"})
    p.write_text(nova_linha + "\n" + "\n".join(original_lines) + "\n", encoding="utf-8")
    # tentar liquidar "A x B" de novo não deve gerar um segundo settlement
    recs_de_novo = settle_bet("A", "B", 3, 1, path=p)
    assert recs_de_novo == []
    st = summary(path=p)
    assert st["ou25"]["n"] == 1  # não duplicou
    assert st["ou25"]["staked"] == 1.0


def test_settle_placar_none_levanta_valueerror_claro(tmp_path):
    p = tmp_path / "bets.jsonl"
    add_bet("A", "B", "ou25", "over", 2.0, path=p)
    with pytest.raises(ValueError, match="placar inválido"):
        settle_bet("A", "B", None, 1, path=p)


def test_add_bet_naive_vs_aware_nao_crasha(tmp_path):
    p = tmp_path / "bets.jsonl"
    # logged_at sem timezone (erro comum de operador colando horário BR),
    # kickoff com 'Z' — antes disso levantava TypeError não tratado e a
    # aposta não era registrada; agora cai no mesmo tratamento de
    # "timestamp ilegível", registra normalmente com late=None.
    rec = add_bet(
        "A",
        "B",
        "ou25",
        "over",
        2.0,
        kickoff="2026-08-01T19:00:00Z",
        logged_at="2026-08-01T16:00:00",  # naive, sem offset
        path=p,
    )
    assert rec["kind"] == "bet"
    assert rec["late"] is None


def test_capital_gate_status_avisa_sem_trial_comprovada(tmp_path):
    trials = tmp_path / "trials.json"
    trials.write_text(
        json.dumps(
            [
                {"name": "h1", "params": {"market": "ou25"}, "status": "refutada"},
                {"name": "h3", "params": {"market": "ou25"}, "status": "inconclusiva"},
            ]
        ),
        encoding="utf-8",
    )
    warning = capital_gate_status("ou25", trials_path=trials)
    assert warning is not None
    assert "comprovada" in warning


def test_capital_gate_status_silencioso_com_trial_comprovada(tmp_path):
    trials = tmp_path / "trials.json"
    trials.write_text(
        json.dumps([{"name": "h1", "params": {"market": "ou2.5"}, "status": "comprovada"}]),
        encoding="utf-8",
    )
    assert capital_gate_status("ou25", trials_path=trials) is None


def test_capital_gate_status_ignora_mercado_fora_do_gate(tmp_path):
    # ou15 nunca teve funil de CLV desenhado — não é coberto por trial nenhuma,
    # e o gate não deve reclamar de algo que nunca se propôs a validar.
    assert capital_gate_status("ou15", trials_path=tmp_path / "inexistente.json") is None


def test_capital_gate_status_falha_fechado_sem_trials_json(tmp_path):
    warning = capital_gate_status("ou25", trials_path=tmp_path / "nao_existe.json")
    assert warning is not None
    assert "não encontrado" in warning
