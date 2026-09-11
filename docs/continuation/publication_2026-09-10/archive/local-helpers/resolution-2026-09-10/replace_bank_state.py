from pathlib import Path

path = Path('C:/BRASILEIRAO/brasileirao-predictor/brasileirao_predictor/bet_log.py')
source = path.read_text(encoding='utf-8')
start, end = source.index('def bank_state('), source.index('\ndef list_bets(')
replacement = '''def bank_state(bank_path=None, bets_path=None) -> dict | None:
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
    flows = bank_rows[init_index + 1:]
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
        "currency": init["currency"], "initial": init["amount"], "unit": init["unit"],
        "unit_pct": init["unit"] / init["amount"], "flows": net_flows,
        "accounting_scope": "gross_manual_reports_at_historically_declared_unit",
        "drawdown_scope": "cash_flow_adjusted_gross_pnl_and_unitized_nav",
        "economic_evidence_eligible": False, "costs_reconciled": False,
        "profit_units": round(profit_units, 4), "n_settled": len(settlements),
        "open_units": round(open_units, 4), "since": init["at"],
        "valuation_status": "PENDING_RECONCILIATION" if issues else "MANUAL_DECLARATIONS_ONLY",
        "valuation_issues": sorted(set(issues)),
    }
    if issues:
        return {**result, **dict.fromkeys(("balance", "available_money", "profit_money", "open_money", "max_drawdown_money", "max_drawdown_pct"))}
    profit_money = sum(row["profit"] * unit for row, unit in settlements)
    open_money = sum(row["stake"] * unit for row, unit in open_positions)
    equity = peak = float(init["amount"])
    shares, nav_peak, mdd, mdd_pct = equity, 1.0, 0.0, 0.0
    events = [( _timestamp(row["at"]), 0, i, row["amount"] * (1 if row["kind"] == "deposit" else -1)) for i, row in enumerate(flows)]
    events += [(_timestamp(row["recorded_at"]), 1, i, row["profit"] * unit) for i, (row, unit) in enumerate(settlements)]
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
    return {**result, "balance": round(balance, 2), "available_money": round(balance - open_money, 2),
            "profit_money": round(profit_money, 2), "open_money": round(open_money, 2),
            "max_drawdown_money": round(mdd, 2), "max_drawdown_pct": mdd_pct if nav_known else None,
            "nav_status": "COMPUTED" if nav_known else "UNDEFINED_ORDER_OR_NONPOSITIVE_CAPITAL"}


'''
path.write_text(source[:start] + replacement + source[end:], encoding='utf-8')
