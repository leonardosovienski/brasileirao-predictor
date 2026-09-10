"""Livro-caixa de APOSTAS (JSONL append-only) — o elo financeiro do pipeline.

predictions.jsonl congela o que o MODELO disse; este arquivo congela o que o
OPERADOR apostou: seleção, linha, odd tomada, casa, stake. Sem isto não existe
ROI real nem CLV real — só acerto de palpite, que não paga boleto.

Fluxo:
    python -m brasileirao_predictor.bet_log add Norway England ou25 under 2.21 --casa BetOnline \
        --edge 0.095 --prob 0.548                    # ANTES do jogo
    python -m brasileirao_predictor.bet_log settle Norway England 0 1  # depois do placar final
    python -m brasileirao_predictor.bet_log summary                    # ROI acumulado por mercado

Os valores são relatos manuais brutos, sem comprovação de aceitação ou custos.
O campo legado validated identifica o funil histórico, não validação econômica.
CLV depende de fechamento identificado, independente e temporalmente admissível;
não prova lucro futuro. O banco latest-state não fornece esse contrato.
"""

import errno
import json
import math
import os
import uuid
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from functools import wraps
from numbers import Integral, Real
from pathlib import Path

ENV_PATH = "BETS_LOG_PATH"
ENV_BANK_PATH = "BANKROLL_LOG_PATH"
ROOT = Path(__file__).resolve().parent.parent
_DEFAULT = ROOT / "data" / "bets.jsonl"
_BANK_DEFAULT = ROOT / "data" / "bankroll.jsonl"

# guarda-corpos de gestão de banca (flat stake, alinhado ao backtest):
#   unidade > 2% da banca inicial = agressivo demais pra variância real do
#   O/U (3/8 de acerto numa rodada é normal); exposição aberta > 10u = muita
#   banca em jogo ao mesmo tempo. Avisos, não bloqueios — a banca é do operador.
MAX_UNIT_PCT = 0.02
MAX_OPEN_UNITS = 10.0

# mercado -> (linha, período). FT = jogo inteiro; 1T/2T = por tempo (settle
# exige o placar do intervalo). Só o ou25 tem um FUNIL de CLV desenhado no
# backtest (as demais entram como registro fiel do que o operador apostou,
# marcadas validated=False, e o summary separa os dois grupos) — "desenhado"
# não é "comprovado": ver capital_gate_status() pra saber se alguma trial do
# mercado já tem status='comprovada' de verdade em data/trials.json.
MARKETS = {
    "ou25": (2.5, "FT"),
    "ou15": (1.5, "FT"),
    "ou05_1t": (0.5, "1T"),
    "ou15_1t": (1.5, "1T"),
    "ou25_1t": (2.5, "1T"),
    "ou05_2t": (0.5, "2T"),
    "ou15_2t": (1.5, "2T"),
    "ou25_2t": (2.5, "2T"),
}
VALIDATED = {"ou25"}  # único mercado com funil de CLV desenhado

TRIALS_DEFAULT = ROOT / "data" / "trials.json"
# mercado deste ledger -> valores de params.market usados em trials.json
# (a nomenclatura não é 100% uniforme entre trials mais antigas e mais novas)
_GATE_MARKET_ALIASES = {"ou25": {"ou25", "ou2.5"}}


def capital_gate_status(market: str, trials_path=None) -> str | None:
    """Aviso (NUNCA bloqueio — a banca é do operador) quando nenhuma trial
    pré-registrada para `market` em data/trials.json tem status='comprovada'
    ainda. É a regra 2 do README (aposta real só em mercado com CLV
    comprovado no backtest deste domínio) checada contra o registro de
    governança, em vez de confiada à memória de quem está apostando."""
    aliases = _GATE_MARKET_ALIASES.get(market)
    if not aliases:
        return None
    path = Path(trials_path or os.environ.get("TRIALS_LOG_PATH") or TRIALS_DEFAULT)
    if not path.exists():
        return f"trials.json não encontrado em {path} — gate de capital não verificável"
    from predictor_core.contracts.registry import TrialRegistry

    trials = TrialRegistry(path).load()
    relevant = [t for t in trials if t.get("params", {}).get("market") in aliases]
    if any(t.get("status") == "comprovada" for t in relevant):
        return None
    return (
        f"nenhuma trial pré-registrada para o mercado {market!r} tem status='comprovada' em "
        f"{path.name} — a regra 2 (aposta real só com CLV comprovado no backtest deste domínio) "
        "ainda não está satisfeita"
    )


def _resolve(path=None) -> Path:
    return Path(path or os.environ.get(ENV_PATH) or _DEFAULT)


@contextmanager
def _writer_lock(path: Path):
    """Nonblocking OS lock for cooperating writers; keep the sidecar inode.

    The OS releases the lock on process exit. Never delete a live sidecar:
    replacing it could let two writers lock different files for the same book.
    Manual edits and network-filesystem lock semantics are outside this contract.
    """
    lock_path = path.with_name(path.name + ".writer.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as handle:
        if os.name == "nt":
            import msvcrt

            def acquire():
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

            def release():
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

        else:
            import fcntl

            def acquire():
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release():
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        try:
            acquire()
        except OSError as exc:
            raise BlockingIOError(errno.EWOULDBLOCK, "livro indisponível para escrita exclusiva") from exc
        try:
            yield
        finally:
            release()


def _single_writer(resolve):
    def decorate(function):
        @wraps(function)
        def locked(*args, **kwargs):
            path = resolve(kwargs.get("path")).resolve()
            with _writer_lock(path):
                return function(*args, **{**kwargs, "path": path})

        return locked

    return decorate


def _read_records(p: Path, kinds: set[str]) -> list[dict]:
    if not p.exists():
        return []

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("chave JSON duplicada no livro")
            result[key] = value
        return result

    def finite_float(value):
        number = float(value)
        _finite_number(number, "valor JSON")
        return number

    def invalid_constant(value):
        raise ValueError("constante JSON não finita no livro")

    rows = [
        json.loads(line, object_pairs_hook=unique_object, parse_float=finite_float, parse_constant=invalid_constant)
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(
        not isinstance(row, dict) or not isinstance(row.get("kind"), str) or row["kind"] not in kinds for row in rows
    ):
        raise ValueError("registro desconhecido no livro")
    return rows


def _read(path=None) -> list[dict]:
    return _read_records(_resolve(path), {"bet", "settlement"})


def _append(rec: dict, path=None) -> None:
    """Append under the caller's writer lock; never rewrite prior bytes."""
    encoded = (json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    dest = _resolve(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "a+b") as f:
        f.seek(0, os.SEEK_END)
        if f.tell():
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                encoded = b"\n" + encoded
        f.write(encoded)
        f.flush()
        os.fsync(f.fileno())


def _finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} deve ser um número finito")


def _settlement_index(rows):
    bets = {}
    for row in rows:
        if row["kind"] != "bet":
            continue
        for field in ("stake", "odds"):
            _finite_number(row.get(field), field)
        if row["stake"] <= 0 or row["odds"] <= 1:
            raise ValueError("stake ou odd inválida no livro")
        market = row.get("market")
        if not isinstance(market, str) or market not in MARKETS:
            raise ValueError("mercado inválido no livro")
        if (row.get("line"), row.get("period")) != MARKETS[market] or row.get("selection") not in {"over", "under"}:
            raise ValueError("contrato de mercado inconsistente no livro")
        if any(not isinstance(row.get(field), str) or not row[field].strip() for field in ("home", "away")):
            raise ValueError("identidade dos times inválida no livro")
        if row.get("bet_id") is not None:
            identity = row["bet_id"]
            if not isinstance(identity, str) or not identity.strip() or identity in bets:
                raise ValueError("bet_id inválido ou duplicado no livro")
            bets[identity] = row
    by_id, by_line = {}, {}
    for row in rows:
        if row["kind"] != "settlement":
            continue
        if row.get("bet_id"):
            if row["bet_id"] in by_id:
                raise ValueError("bet_id possui liquidações duplicadas; reconciliação necessária")
            by_id[row["bet_id"]] = row
            bet = bets.get(row["bet_id"])
        else:
            index = row.get("bet_line_no")
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(rows):
                raise ValueError("linha legada inválida")
            if index in by_line:
                raise ValueError("linha legada possui liquidações duplicadas")
            by_line[index] = row
            bet = rows[index]
            if bet.get("bet_id"):
                raise ValueError("liquidação legada não pode substituir bet_id")
        if bet is None or bet.get("kind") != "bet":
            raise ValueError("liquidação sem aposta correspondente")
        if any(row.get(field) != bet.get(field) for field in ("home", "away", "market", "selection", "odds", "stake")):
            raise ValueError("liquidação diverge da aposta correspondente")
        for field in ("stake", "odds", "profit"):
            _finite_number(row.get(field), field)
        if row.get("clv_close") is not None:
            _finite_number(row["clv_close"], "clv_close")
        won = row.get("won")
        if "won" not in row or (won is not None and not isinstance(won, bool)):
            raise ValueError("resultado da liquidação inválido")
        expected = 0.0 if won is None else bet["stake"] * (bet["odds"] - 1) if won else -bet["stake"]
        if not math.isclose(row["profit"], expected, rel_tol=0, abs_tol=0.000050001):
            raise ValueError("lucro bruto não reconcilia com stake, odd e resultado")
    return by_id, by_line


def _goal_count(value):
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise ValueError("placar inválido: exige contagem inteira não negativa")
    return int(value)


@_single_writer(_resolve)
def add_bet(
    home,
    away,
    market,
    selection,
    odds,
    *,
    book=None,
    stake=1.0,
    model_prob=None,
    edge=None,
    match_date=None,
    kickoff=None,
    note=None,
    path=None,
    logged_at=None,
    bet_id=None,
) -> dict:
    """Registra a aposta ANTES do jogo. `market` em MARKETS; `selection` é o
    lado ('over'/'under'). `odds` é a odd DECIMAL tomada de fato (line shopping:
    a melhor que você conseguiu, não a média). `kickoff` = ISO-8601 UTC do
    apito — habilita a contagem regressiva no `list` e o carimbo de
    integridade: aposta registrada APÓS o kickoff é marcada late=True (o
    edge 'pré-jogo' dela não vale e o CLV vira mentira)."""
    if market not in MARKETS:
        raise ValueError(f"mercado desconhecido: {market!r} — use um de {sorted(MARKETS)}")
    _finite_number(odds, "odd")
    _finite_number(stake, "stake")
    if not isinstance(selection, str) or selection.lower() not in {"over", "under"}:
        raise ValueError("selection deve ser over ou under")
    if model_prob is not None:
        _finite_number(model_prob, "model_prob")
        if not 0 <= model_prob <= 1:
            raise ValueError("model_prob deve estar entre 0 e 1")
    if edge is not None:
        _finite_number(edge, "edge")
    if odds <= 1.0:
        raise ValueError(f"odd decimal inválida: {odds}")
    if stake <= 0:
        raise ValueError(f"stake inválido: {stake} — tem que ser positivo (stake negativo corrompe ROI e exposição)")
    # Trava OPT-IN (auditoria 2026-07-09): mercados sem CLV validado usam o
    # mesmo stake das validadas por padrão (decisão do operador — o rodapé do
    # odds_shop já sugere 'aposte menor'). Se o operador quiser impor o teto,
    # seta BETLOG_MAX_INFO_STAKE (em unidades); sem a env var, nada muda.
    cap = os.environ.get("BETLOG_MAX_INFO_STAKE")
    if cap is not None and market not in VALIDATED:
        cap_value = float(cap)
        _finite_number(cap_value, "BETLOG_MAX_INFO_STAKE")
        if cap_value < 0:
            raise ValueError("BETLOG_MAX_INFO_STAKE deve ser não negativo")
    if cap is not None and market not in VALIDATED and float(stake) > float(cap):
        raise ValueError(
            f"stake {stake}u excede o teto de {cap}u para mercado SEM CLV "
            f"validado ({market}) — teto definido em BETLOG_MAX_INFO_STAKE"
        )
    line, period = MARKETS[market]
    now_iso = logged_at or datetime.now(UTC).isoformat(timespec="seconds")
    late = None
    if kickoff:
        try:
            ko = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
            late = now >= ko
        except (ValueError, TypeError):
            # ValueError: string ilegível. TypeError: comparar naive x aware
            # (ex.: logged_at colado sem timezone) — auditoria hostil
            # 2026-07-17: antes só ValueError era pego, TypeError propagava
            # cru e abortava add_bet inteiro sem registrar a aposta.
            kickoff, late = None, None  # timestamp ilegível/ambíguo: ignora, não trava
    # aviso de bilhete duplicado: mesma partida+mercado+seleção ainda aberta
    from .predict import _canon

    target = frozenset((_canon(home), _canon(away)))
    rows = _read(path)
    if bet_id is not None and (
        not isinstance(bet_id, str) or not bet_id.strip() or any(r.get("bet_id") == bet_id for r in rows)
    ):
        raise ValueError("bet_id inválido ou já registrado")
    settled_ids, settled_lines = _settlement_index(rows)
    dup = any(
        r["kind"] == "bet"
        and (r.get("bet_id") not in settled_ids if r.get("bet_id") else i not in settled_lines)
        and frozenset((_canon(r["home"]), _canon(r["away"]))) == target
        and r["market"] == market
        and r["selection"] == selection.lower()
        for i, r in enumerate(rows)
    )
    rec = {
        # W2 (auditoria 2026-07-09, fechado 2026-07-11): identificador ÚNICO da
        # aposta — schema ADITIVO: apostas antigas não têm a chave e o vínculo
        # legado por bet_line_no segue sendo a fonte da liquidação; o bet_id é
        # a rastreabilidade que sobrevive a qualquer contexto fora do arquivo
        # (planilha do operador, telemetria, futuro Ledger do core).
        # `bet_id` injetável para teste determinístico.
        "bet_id": bet_id or str(uuid.uuid4()),
        "logged_at": now_iso,
        "kind": "bet",
        "status": "open",
        "home": home,
        "away": away,
        "match_date": match_date,
        "kickoff": kickoff,
        "late": late,
        "market": market,
        "line": line,
        "period": period,
        "selection": selection.lower(),
        "odds": float(odds),
        "book": book,
        "stake": float(stake),
        "model_prob": model_prob,
        "edge": edge,
        "note": note,
        "validated": market in VALIDATED,
        "duplicate_of_open": dup,
    }
    _append(rec, path)
    return rec


@_single_writer(_resolve)
def settle_bet(
    home, away, home_score, away_score, *, ht=None, path=None, recorded_at=None, match_date=None
) -> list[dict]:
    """Fecha as apostas abertas deste confronto contra o placar final.
    Grava uma linha 'settlement' por aposta (append-only — a aposta original
    não é editada). Devolve os settlements gravados.

    `ht` = placar do intervalo (tupla ou 'H-A'), na MESMA ordem casa/fora do
    placar final informado — obrigatório pra fechar apostas de 1T/2T; sem ele
    essas ficam abertas (aviso no CLI), as de jogo inteiro fecham normal.

    `match_date` desambigua confronto REPETIDO (turno x returno, ou dois jogos
    do mesmo par de times — auditoria hostil 2026-07-17: frozenset(casa,fora)
    sozinho não distingue as duas partidas, e fechar sem desambiguar liquidava
    AMBAS com o mesmo placar, inclusive a que ainda não tinha acontecido). Se
    houver mais de uma data distinta entre as apostas abertas candidatas e
    `match_date` não for informado, a função recusa a liquidação em vez de
    adivinhar."""
    from .predict import _canon

    home_score, away_score = _goal_count(home_score), _goal_count(away_score)
    if isinstance(ht, str):
        ht = ht.split("-")
    if ht is not None:
        if not isinstance(ht, (tuple, list)) or len(ht) != 2:
            raise ValueError("placar inválido: intervalo exige dois valores")
        ht = tuple(_goal_count(value) for value in ht)
    if ht is not None and (int(ht[0]) > home_score or int(ht[1]) > away_score):
        raise ValueError("placar do intervalo por time não pode exceder o placar final")
    total_ft = home_score + away_score
    total_ht = None if ht is None else int(ht[0]) + int(ht[1])
    if total_ht is not None and total_ht > total_ft:
        raise ValueError(
            f"placar do intervalo ({total_ht} gols) maior que o final "
            f"({total_ft}) — erro de digitação? dinheiro real exige "
            "placar certo"
        )
    target = frozenset((_canon(home), _canon(away)))
    open_ids = {}
    rows = _read(path)
    settled_bet_ids, settled_ids = _settlement_index(rows)
    for i, r in enumerate(rows):
        key = frozenset((_canon(r["home"]), _canon(r["away"])))
        if r["kind"] == "bet" and key == target:
            open_ids[i] = r

    def _already_settled(i, b):
        # W? (auditoria hostil 2026-07-17): bet_id é estável e sobrevive a
        # reescrita/reordenação do arquivo; bet_line_no (posição) só é usado
        # como fallback para apostas legadas pré-W2 sem bet_id. Confiar só na
        # posição permitia pagar a MESMA aposta duas vezes se o arquivo fosse
        # reescrito com uma linha nova inserida antes das existentes.
        if b.get("bet_id"):
            return b["bet_id"] in settled_bet_ids
        return i in settled_ids

    candidates = {i: b for i, b in open_ids.items() if not _already_settled(i, b)}
    dates: set[str] = {
        str(value) for bet in candidates.values() if (value := bet.get("match_date") or (bet.get("kickoff") or "")[:10])
    }
    if match_date is None and len(dates) > 1:
        raise ValueError(
            f"confronto {home} x {away} tem apostas abertas de {len(dates)} datas "
            f"diferentes ({sorted(dates)}) — passe match_date para desambiguar "
            "qual jogo está sendo liquidado (turno/returno ou confronto repetido)"
        )
    if match_date is not None:
        candidates = {
            i: b
            for i, b in candidates.items()
            if (b.get("match_date") or (b.get("kickoff") or "")[:10] or None) == match_date
        }
    out = []
    for line_no, bet in candidates.items():
        period = bet.get("period", "FT")
        if period == "FT":
            total = total_ft
        elif total_ht is None:
            continue  # 1T/2T sem HT informado: segue aberta
        else:
            total = total_ht if period == "1T" else total_ft - total_ht
        won = (
            (bet["selection"] == "over") == (total > bet["line"]) if total != bet["line"] else None
        )  # push só em linha inteira
        profit = 0.0 if won is None else round(bet["stake"] * (bet["odds"] - 1.0), 4) if won else -bet["stake"]
        # Não inferir um fechamento de estado latest-state e aliases aproximados.
        # Relatos antigos ficam intactos; novas liquidações exigiriam um contrato
        # de preço independente e temporalmente admissível para calcular CLV.
        clv = None
        reverse = _canon(bet["home"]) != _canon(home)
        score_pair = (away_score, home_score) if reverse else (home_score, away_score)
        ht_pair = None if ht is None else ht[::-1] if reverse else ht
        rec = {
            "recorded_at": recorded_at or datetime.now(UTC).isoformat(timespec="seconds"),
            "kind": "settlement",
            "bet_line_no": line_no,
            # W2: carimba o id da aposta fechada (None = aposta legada pré-W2)
            "bet_id": bet.get("bet_id"),
            "home": bet["home"],
            "away": bet["away"],
            "score": f"{score_pair[0]}-{score_pair[1]}",
            "ht": None if ht_pair is None else f"{ht_pair[0]}-{ht_pair[1]}",
            "total_do_periodo": total,
            "market": bet["market"],
            "period": period,
            "selection": bet["selection"],
            "odds": bet["odds"],
            "stake": bet["stake"],
            "won": won,
            "profit": profit,
            "clv_close": clv,
            "clv_status": "UNAVAILABLE_NO_ADMISSIBLE_CLOSING",
            "economic_evidence_eligible": False,
            "costs_reconciled": False,
            "validated": bet.get("validated", bet["market"] in VALIDATED),
        }
        _append(rec, path)
        out.append(rec)
    return out


def _resolve_bank(path=None) -> Path:
    return Path(path or os.environ.get(ENV_BANK_PATH) or _BANK_DEFAULT)


def _timestamp(value) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp exige ISO-8601 com timezone")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp exige timezone explícito")
    return result.astimezone(UTC)


def _read_bank(path) -> list[dict]:
    rows = _read_records(_resolve_bank(path), {"init", "deposit", "withdraw"})
    previous = None
    initialized = False
    for row in rows:
        _finite_number(row.get("amount"), "valor bancário")
        if row["amount"] <= 0:
            raise ValueError("valor bancário deve ser positivo")
        timestamp = _timestamp(row.get("at"))
        if previous is not None and timestamp < previous:
            raise ValueError("cronologia bancária fora de ordem; reconciliação necessária")
        previous = timestamp
        if row["kind"] == "init":
            initialized = True
            _finite_number(row.get("unit"), "unidade")
            if row["unit"] <= 0:
                raise ValueError("unidade deve ser positiva")
            if not isinstance(row.get("currency"), str) or not row["currency"].strip():
                raise ValueError("moeda deve ser declarada")
        elif not initialized:
            raise ValueError("fluxo bancário exige abertura anterior")
    return rows


def _bank_clock(rows, at):
    stamp = _timestamp(at)
    if rows and stamp < _timestamp(rows[-1]["at"]):
        raise ValueError("cronologia bancária não permite lançamento retroativo")
    return stamp


@_single_writer(_resolve_bank)
def bank_init(amount, unit, *, currency="BRL", path=None, at=None) -> dict:
    """Abre (ou reabre) a banca: valor total e valor da UNIDADE em dinheiro.
    Append-only — um novo init reinicia a contagem a partir dele (o histórico
    anterior fica no arquivo, auditável)."""
    _finite_number(amount, "banca")
    _finite_number(unit, "unidade")
    if amount <= 0 or unit <= 0:
        raise ValueError("banca e unidade devem ser positivas")
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("moeda deve ser declarada")
    rows = _read_bank(path)
    rec = {
        "at": at or datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": "init",
        "amount": float(amount),
        "unit": float(unit),
        "currency": currency,
    }
    _bank_clock(rows, rec["at"])
    _append(rec, _resolve_bank(path))
    return rec


@_single_writer(_resolve_bank)
def bank_flow(kind, amount, *, path=None, at=None) -> dict:
    """Depósito ou saque (kind='deposit'|'withdraw')."""
    if kind not in ("deposit", "withdraw"):
        raise ValueError(f"kind inválido: {kind}")
    _finite_number(amount, "valor")
    if amount <= 0:
        raise ValueError("valor deve ser positivo")
    rows = _read_bank(path)
    if not rows:
        raise ValueError("fluxo bancário exige abertura anterior")
    rec = {
        "at": at or datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": kind,
        "amount": float(amount),
    }
    _bank_clock(rows, rec["at"])
    _append(rec, _resolve_bank(path))
    return rec


def bank_state(bank_path=None, bets_path=None) -> dict | None:
    """Coherent snapshot of both manual books, with historically declared units.

    A new init resets the cash anchor, never the monetary size of an old bet.
    Missing or ambiguous unit/currency history blocks monetary valuation. Locks
    coordinate our local writers only; manual edits are outside this contract.
    """
    bank, bets = _resolve_bank(bank_path).resolve(), _resolve(bets_path).resolve()
    if bank == bets:
        raise ValueError("banca e apostas exigem livros distintos")
    with ExitStack() as locks:
        for path in sorted({bank, bets}, key=lambda item: str(item).casefold()):
            locks.enter_context(_writer_lock(path))
        bank_rows = _read_bank(bank)
        if not bank_rows:
            return None
        all_rows = _read(bets)
    return _bank_snapshot(bank_rows, all_rows)


def _bank_snapshot(bank_rows, all_rows):
    inits = [row for row in bank_rows if row["kind"] == "init"]
    init = inits[-1]
    init_at = _timestamp(init["at"])
    init_index = max(i for i, row in enumerate(bank_rows) if row["kind"] == "init")
    flows = bank_rows[init_index + 1 :]
    net_flows = sum(row["amount"] * (1 if row["kind"] == "deposit" else -1) for row in flows)
    settled_ids, settled_lines = _settlement_index(all_rows)
    issues, settlements, open_positions = [], [], []

    def value_unit(bet):
        try:
            at = _timestamp(bet.get("logged_at"))
        except ValueError:
            issues.append("aposta sem horário de registro válido")
            return None
        regimes = [row for row in inits if _timestamp(row["at"]) <= at]
        if not regimes:
            issues.append("aposta anterior à primeira unidade monetária declarada")
            return None
        last_at = _timestamp(regimes[-1]["at"])
        values = {(row["currency"], row["unit"]) for row in regimes if _timestamp(row["at"]) == last_at}
        if len(values) != 1:
            issues.append("unidades conflitantes no mesmo horário de registro")
            return None
        currency, unit = values.pop()
        if currency != init["currency"]:
            issues.append("moeda histórica diferente; conversão não comprovada")
            return None
        return unit

    for index, bet in enumerate(all_rows):
        if bet["kind"] != "bet":
            continue
        settlement = settled_ids.get(bet["bet_id"]) if bet.get("bet_id") else settled_lines.get(index)
        if settlement is None:
            open_positions.append((bet, value_unit(bet)))
        elif _timestamp(settlement["recorded_at"]) >= init_at:
            if _timestamp(settlement["recorded_at"]) < _timestamp(bet.get("logged_at")):
                raise ValueError("liquidação anterior ao registro da aposta")
            settlements.append((settlement, value_unit(bet)))
    profit_units = sum(row["profit"] for row, _ in settlements)
    open_units = sum(row["stake"] for row, _ in open_positions)
    result = {
        "currency": init["currency"],
        "initial": init["amount"],
        "unit": init["unit"],
        "unit_pct": init["unit"] / init["amount"],
        "flows": net_flows,
        "accounting_scope": "gross_manual_reports_at_historically_declared_unit",
        "drawdown_scope": "cash_flow_adjusted_gross_pnl_and_unitized_nav",
        "economic_evidence_eligible": False,
        "costs_reconciled": False,
        "profit_units": round(profit_units, 4),
        "n_settled": len(settlements),
        "open_units": round(open_units, 4),
        "since": init["at"],
        "valuation_status": "PENDING_RECONCILIATION" if issues else "MANUAL_DECLARATIONS_ONLY",
        "valuation_issues": sorted(set(issues)),
    }
    if issues:
        return {
            **result,
            **dict.fromkeys(
                ("balance", "available_money", "profit_money", "open_money", "max_drawdown_money", "max_drawdown_pct")
            ),
        }
    profit_money = sum(row["profit"] * unit for row, unit in settlements)
    open_money = sum(row["stake"] * unit for row, unit in open_positions)
    equity = peak = float(init["amount"])
    shares, nav_peak, mdd, mdd_pct = equity, 1.0, 0.0, 0.0
    events = [
        (_timestamp(row["at"]), 0, i, row["amount"] * (1 if row["kind"] == "deposit" else -1))
        for i, row in enumerate(flows)
    ]
    events += [
        (_timestamp(row["recorded_at"]), 1, i, row["profit"] * unit) for i, (row, unit) in enumerate(settlements)
    ]
    flow_times = {at for at, kind, _, _ in events if kind == 0}
    nav_known = not any(at in flow_times for at, kind, _, _ in events if kind == 1)
    for _, kind, _, amount in sorted(events):
        if kind == 0:
            if equity <= 0 or shares <= 0 or equity + amount <= 0:
                nav_known = False
            elif nav_known:
                shares += amount / (equity / shares)
            equity += amount
            peak += amount
        else:
            equity += amount
            peak = max(peak, equity)
            mdd = max(mdd, peak - equity)
            if equity < 0 or shares <= 0:
                nav_known = False
            elif nav_known:
                nav = equity / shares
                nav_peak = max(nav_peak, nav)
                mdd_pct = max(mdd_pct, 1 - nav / nav_peak)
    balance = init["amount"] + net_flows + profit_money
    for value in (balance, profit_money, open_money, mdd, mdd_pct):
        _finite_number(value, "reconciliação monetária")
    if not math.isclose(equity, balance, rel_tol=1e-12, abs_tol=1e-8):
        raise ArithmeticError("saldo não reconcilia com os eventos")
    return {
        **result,
        "balance": round(balance, 2),
        "available_money": round(balance - open_money, 2),
        "profit_money": round(profit_money, 2),
        "open_money": round(open_money, 2),
        "max_drawdown_money": round(mdd, 2),
        "max_drawdown_pct": mdd_pct if nav_known else None,
        "nav_status": "COMPUTED" if nav_known else "UNDEFINED_ORDER_OR_NONPOSITIVE_CAPITAL",
    }


def list_bets(path=None) -> list[dict]:
    """Todas as apostas com status resolvido por linha: cada bet ganha
    'result' (settlement casado por bet_line_no) ou None se aberta."""
    rows = _read(path)
    settled_ids, settled_lines = _settlement_index(rows)
    out = []
    for i, r in enumerate(rows):
        if r["kind"] != "bet":
            continue
        result = settled_ids.get(r["bet_id"]) if r.get("bet_id") else settled_lines.get(i)
        out.append({**r, "result": result})
    return out


def _countdown(kickoff: str | None) -> str:
    """'em 3h12', 'em 2d 04h', 'EM ANDAMENTO/ENCERRADO' ou '' sem kickoff."""
    if not kickoff:
        return ""
    try:
        ko = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
        if ko.tzinfo is None or ko.utcoffset() is None:
            return ""
    except ValueError:
        return ""
    delta = (ko - datetime.now(UTC)).total_seconds()
    if delta <= 0:
        return "JÁ COMEÇOU"
    d, rem = divmod(int(delta), 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    return f"em {d}d {h:02d}h" if d else (f"em {h}h{m:02d}" if h else f"em {m}min")


def summary(path=None) -> dict:
    """ROI e CLV acumulados por mercado (só apostas fechadas). A chave carrega
    o grupo: mercado validado (ou25) separado dos informativos — misturar os
    dois esconderia um ROI negativo atrás do outro."""
    tally: dict = {}
    rows = _read(path)
    _settlement_index(rows)
    for r in rows:
        if r["kind"] != "settlement":
            continue
        t = tally.setdefault(
            r["market"],
            {
                "n": 0,
                "staked": 0.0,
                "profit": 0.0,
                "clv_sum": 0.0,
                "clv_n": 0,
                "validated": r.get("validated", False),
                "accounting_scope": "gross_manual_reports",
                "economic_evidence_eligible": False,
                "costs_reconciled": False,
                "clv_scope": "legacy_unverified_reports",
            },
        )
        t["n"] += 1
        t["staked"] += r["stake"]
        t["profit"] += r["profit"]
        if r.get("clv_close") is not None:
            t["clv_sum"] += r["clv_close"]
            t["clv_n"] += 1
    for t in tally.values():
        t["roi"] = t["profit"] / t["staked"] if t["staked"] else 0.0
        t["clv_medio"] = t["clv_sum"] / t["clv_n"] if t["clv_n"] else None
    return tally


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Livro-caixa de apostas (append-only)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="registra aposta ANTES do jogo")
    a.add_argument("home")
    a.add_argument("away")
    a.add_argument("market", choices=sorted(MARKETS))
    a.add_argument("selection", choices=["over", "under"])
    a.add_argument("odds", type=float)
    a.add_argument("--casa", dest="book")
    a.add_argument("--stake", type=float, default=1.0)
    a.add_argument("--prob", type=float, dest="model_prob")
    a.add_argument("--edge", type=float)
    a.add_argument("--date", dest="match_date")
    a.add_argument(
        "--kickoff",
        help="ISO-8601 UTC do apito (habilita contagem regressiva e o carimbo de aposta tardia)",
    )
    a.add_argument("--nota", dest="note")

    sub.add_parser("list", help="todas as apostas: abertas com contagem regressiva, fechadas com resultado")

    s = sub.add_parser("settle", help="fecha apostas do confronto no placar final")
    s.add_argument("home")
    s.add_argument("away")
    s.add_argument("home_score", type=int)
    s.add_argument("away_score", type=int)
    s.add_argument("--ht", help="placar do intervalo 'H-A' (obrigatório pra fechar apostas de 1T/2T)")
    s.add_argument(
        "--date",
        dest="match_date",
        help="data do jogo (YYYY-MM-DD) — obrigatório se houver "
        "apostas abertas do mesmo confronto em datas diferentes "
        "(turno/returno)",
    )

    sub.add_parser("summary", help="ROI/CLV acumulado por mercado")

    b = sub.add_parser("banca", help="painel da banca (saldo/exposição/drawdown)")
    b.add_argument("--init", type=float, metavar="VALOR", help="abre a banca com este valor total")
    b.add_argument("--unidade", type=float, help="valor da unidade em dinheiro (com --init)")
    b.add_argument("--deposito", type=float, metavar="VALOR")
    b.add_argument("--saque", type=float, metavar="VALOR")
    b.add_argument("--moeda", default="BRL")

    args = ap.parse_args()
    if args.cmd == "add":
        rec = add_bet(
            args.home,
            args.away,
            args.market,
            args.selection,
            args.odds,
            book=args.book,
            stake=args.stake,
            model_prob=args.model_prob,
            edge=args.edge,
            match_date=args.match_date,
            kickoff=args.kickoff,
            note=args.note,
        )
        aviso = "" if rec["validated"] else "  [mercado SEM CLV validado]"
        gate = capital_gate_status(args.market)
        if gate:
            print(f"  AVISO: {gate} — isto NÃO bloqueia o registro, a banca é do operador")
        print(
            f"registrada [{rec['bet_id'][:8]}]: {rec['selection']} {rec['line']} "
            f"({rec['period']}) @ {rec['odds']} "
            f"({rec['book'] or 'casa nao informada'}) "
            f"stake {rec['stake']}u — {rec['home']} x {rec['away']}{aviso}"
        )
        if rec["late"]:
            print(
                "  ALERTA: registrada APÓS o kickoff — o edge pré-jogo desta "
                "aposta NÃO vale e ela ficou carimbada late=True no livro."
            )
        if rec["duplicate_of_open"]:
            print(
                "  ALERTA: já existe aposta ABERTA idêntica (mesmo jogo/mercado/"
                "lado) — se foi sem querer, a exposição dobrou."
            )
    elif args.cmd == "list":
        st = bank_state()
        unit = st["unit"] if st else None
        bets = list_bets()
        if not bets:
            print("nenhuma aposta no livro ainda")
            return
        abertas = [b for b in bets if b["result"] is None]
        fechadas = [b for b in bets if b["result"] is not None]
        if abertas:
            print(f"\n=== ABERTAS ({len(abertas)}) ===")
            for b in abertas:
                v = "funil legado" if b.get("validated", b["market"] in VALIDATED) else "informativo"
                money = f" = R$ {b['stake'] * unit:.0f}" if unit else ""
                extra = " ".join(
                    x
                    for x in (
                        _countdown(b.get("kickoff")) or (b.get("match_date") or ""),
                        "[LATE]" if b.get("late") else "",
                        "[DUP?]" if b.get("duplicate_of_open") else "",
                    )
                    if x
                )
                print(
                    f"  [{v}] {b['home']} x {b['away']}: {b['selection']} "
                    f"{b['line']} ({b.get('period', 'FT')}) @ {b['odds']} "
                    f"{b['book'] or ''} | {b['stake']}u{money} | {extra}"
                )
        if fechadas:
            print(f"\n=== FECHADAS ({len(fechadas)}) ===")
            for b in fechadas:
                r = b["result"]
                res = "PUSH" if r["won"] is None else ("GANHOU" if r["won"] else "PERDEU")
                money = f" = R$ {r['profit'] * unit:+.0f}" if unit else ""
                clv = f" | CLV {r['clv_close']:+.1%}" if r.get("clv_close") is not None else ""
                print(
                    f"  [{res}] {b['home']} x {b['away']}: {b['selection']} "
                    f"{b['line']} ({b.get('period', 'FT')}) @ {b['odds']} "
                    f"-> {r['profit']:+.2f}u{money}{clv}"
                )
        if st:
            print(
                f"\n  banca: R$ {st['balance']:.2f} | em jogo: {st['open_units']:.1f}u "
                f"= R$ {st['open_money']:.2f} | unidade R$ {st['unit']:.2f}"
            )
    elif args.cmd == "settle":
        recs = settle_bet(
            args.home,
            args.away,
            args.home_score,
            args.away_score,
            ht=args.ht,
            match_date=args.match_date,
        )
        if not recs:
            print("nenhuma aposta aberta para este confronto")
        for r in recs:
            res = "PUSH" if r["won"] is None else ("GANHOU" if r["won"] else "PERDEU")
            clv = "" if r["clv_close"] is None else f" | CLV {r['clv_close']:+.2%}"
            print(f"{res}: {r['selection']} {r['market']} ({r['period']}) @ {r['odds']} -> {r['profit']:+.2f}u{clv}")
        if recs and args.ht is None:
            print("(apostas de 1T/2T, se houver, seguem abertas — repita com --ht H-A)")
    elif args.cmd == "banca":
        if args.init is not None:
            if args.unidade is None:
                ap.error("--init exige --unidade (valor da unidade em dinheiro)")
            rec = bank_init(args.init, args.unidade, currency=args.moeda)
            pct = args.unidade / args.init
            print(
                f"banca aberta: {rec['amount']:.2f} {rec['currency']} | "
                f"unidade = {rec['unit']:.2f} ({pct:.1%} da banca)"
            )
            if pct > MAX_UNIT_PCT:
                print(
                    f"  AVISO: unidade acima de {MAX_UNIT_PCT:.0%} da banca — "
                    "3 derrotas em 8 apostas é variância NORMAL do O/U; "
                    "unidade grande transforma variância em ruína."
                )
        if args.deposito:
            bank_flow("deposit", args.deposito)
            print(f"depósito: +{args.deposito:.2f}")
        if args.saque:
            bank_flow("withdraw", args.saque)
            print(f"saque: -{args.saque:.2f}")
        st = bank_state()
        if st is None:
            print(
                "banca não aberta — use: python -m brasileirao_predictor.bet_log banca "
                "--init VALOR --unidade VALOR_DA_UNIDADE"
            )
            return
        cur = st["currency"]
        print(f"\n=== BANCA ({cur}) — desde {st['since'][:10]} ===")
        if st["valuation_status"] == "PENDING_RECONCILIATION":
            print("Valores monetários indisponíveis: " + "; ".join(st["valuation_issues"]))
            return
        fluxos = f", fluxos {st['flows']:+.2f}" if st["flows"] else ""
        print(f"  saldo atual:      {st['balance']:.2f}  (inicial {st['initial']:.2f}{fluxos})")
        print(f"  unidade:          {st['unit']:.2f}  ({st['unit_pct']:.1%} da banca inicial)")
        print(
            f"  resultado:        {st['profit_units']:+.2f}u = {st['profit_money']:+.2f} {cur}"
            f"  em {st['n_settled']} apostas fechadas"
        )
        print(f"  em jogo (aberto): {st['open_units']:.1f}u = {st['open_money']:.2f} {cur}")
        print(f"  drawdown máximo:  {st['max_drawdown_money']:.2f} {cur}")
        if st["unit_pct"] > MAX_UNIT_PCT:
            print(f"  AVISO: unidade > {MAX_UNIT_PCT:.0%} da banca inicial")
        if st["open_units"] > MAX_OPEN_UNITS:
            print(f"  AVISO: exposição aberta > {MAX_OPEN_UNITS:.0f}u")
    else:
        tally = summary()
        print("Relatos manuais brutos: sem comprovação de aceitação, custos ou rentabilidade.")
        if not tally:
            print("nenhuma aposta fechada ainda (data/bets.jsonl)")
        for grupo, ok in (
            ("MERCADO DO FUNIL LEGADO (flag técnica, sem certificação econômica)", True),
            ("OUTROS MERCADOS REGISTRADOS", False),
        ):
            linhas = {m: t for m, t in tally.items() if t["validated"] == ok}
            if not linhas:
                continue
            print(f"\n{grupo}:")
            for m, t in linhas.items():
                clv = "sem odd de fechamento" if t["clv_medio"] is None else f"CLV médio {t['clv_medio']:+.2%}"
                print(
                    f"  {m}: {t['n']} apostas | staked {t['staked']:.1f}u | "
                    f"lucro {t['profit']:+.2f}u | ROI {t['roi']:+.1%} | {clv}"
                )


if __name__ == "__main__":
    main()
