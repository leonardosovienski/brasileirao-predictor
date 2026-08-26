"""
paper_ledger.py — Ledger imutável de paper-trading com CLV.
Regras (herdadas do protocolo):
- toda aposta registrada ANTES do resultado ser conhecido (ts_capture < kickoff)
- flat stake sempre
- CLV obrigatório: odd de fechamento Pinnacle registrada ao fechar o mercado
- saída máxima: CAPITAL_GATE = LOCKED | ELIGIBLE_FOR_REVIEW (decisão humana)
"""

import hashlib
import json
import math
import os
from datetime import datetime

import numpy as np
from bet_engine import dsr, psr, roi_ic_bootstrap, sharpe_de_retornos


class PaperLedger:
    def __init__(self, path="paper_ledger.jsonl", trials_declarados=10, gate_dsr=0.95):
        self.path = path
        self.trials = trials_declarados  # declarar ex ante; alimenta o DSR
        self.gate = gate_dsr

    def registrar_aposta(self, event_id, market, selection, book, odd, ts_capture, kickoff, stake=1.0):
        if stake != 1.0:
            raise ValueError("paper-trading exige stake flat de 1.0")
        self._validate_datetime(ts_capture, "ts_capture")
        self._validate_datetime(kickoff, "kickoff")
        if ts_capture >= kickoff:
            raise ValueError("VIOLAÇÃO PIT: aposta registrada após kickoff")
        if not math.isfinite(odd) or odd <= 1.0:
            raise ValueError("odd deve ser finita e maior que 1.0")
        if any(
            (record["event_id"], record["market"], record["selection"]) == (event_id, market, selection)
            for record in self._load()
        ):
            raise ValueError("aposta duplicada para o mesmo evento e seleção")
        rec = {
            "type": "bet",
            "event_id": event_id,
            "market": market,
            "selection": selection,
            "book": book,
            "odd": odd,
            "ts_capture": ts_capture.isoformat(),
            "kickoff": kickoff.isoformat(),
            "stake": stake,
            "closing_odd": None,
            "result": None,
            "ret": None,
        }
        self._append(rec)
        return rec

    def registrar_fechamento(self, event_id, market, selection, closing_odd):
        """Atualiza o registro com a odd de fechamento Pinnacle (base do CLV)."""
        if not math.isfinite(closing_odd) or closing_odd <= 1.0:
            raise ValueError("closing_odd deve ser finita e maior que 1.0")
        self._update(event_id, market, selection, {"closing_odd": closing_odd})

    def liquidar(self, event_id, market, selection, acertou):
        recs = self._load()
        record = self._find(recs, event_id, market, selection)
        if record["closing_odd"] is None:
            raise ValueError("liquidar sem closing_odd (CLV) é proibido")
        if record["result"] is not None:
            raise ValueError("aposta já liquidada")
        self._update(
            event_id,
            market,
            selection,
            {
                "result": "win" if acertou else "loss",
                "ret": (record["odd"] - 1) * record["stake"] if acertou else -record["stake"],
            },
        )

    def relatorio(self):
        recs = [r for r in self._load() if r.get("ret") is not None]
        if len(recs) < 2:
            return {"status": "insuficiente", "n": len(recs)}
        rets = np.array([r["ret"] for r in recs])
        clvs = np.array([r["odd"] / r["closing_odd"] - 1 for r in recs])
        roi, ic = roi_ic_bootstrap(rets)
        from scipy import stats as st

        sk, ku = float(st.skew(rets)), float(st.kurtosis(rets) + 3)
        sr = sharpe_de_retornos(rets)
        d = dsr(self.trials, sr, len(rets), sk, ku)
        return {
            "n": len(recs),
            "roi": round(roi, 4),
            "roi_ic95": [round(x, 4) for x in ic],
            "clv_medio": round(float(clvs.mean()), 4),
            "clv_pct_positivo": round(float((clvs > 0).mean()), 4),
            "sharpe": round(sr, 4),
            "psr": round(psr(sr, 0, len(rets), sk, ku), 4),
            "dsr": round(d, 4),
            "CAPITAL_GATE": "ELIGIBLE_FOR_REVIEW" if (d >= self.gate and clvs.mean() > 0 and ic[0] > 0) else "LOCKED",
        }

    def _append(self, rec):
        rec["hash_prev"] = self._last_hash()
        line = json.dumps(rec, ensure_ascii=False)
        with open(self.path, "a") as f:
            f.write(line + "\n")

    def _last_hash(self):
        if not os.path.exists(self.path):
            return "GENESIS"
        with open(self.path) as f:
            lines = f.read().strip().split("\n")
        return hashlib.sha256(lines[-1].encode()).hexdigest()[:16] if lines and lines[0] else "GENESIS"

    def _load(self):
        if not os.path.exists(self.path):
            return []
        records = {}
        with open(self.path) as ledger:
            for line in ledger:
                if not line.strip():
                    continue
                raw = json.loads(line)
                key = (raw["event_id"], raw["market"], raw["selection"])
                if raw["type"] == "bet":
                    records[key] = raw
                elif raw["type"] == "update" and key in records:
                    records[key].update(raw["fields"])
        return list(records.values())

    def _update(self, event_id, market, selection, fields):
        self._find(self._load(), event_id, market, selection)
        self._append(
            {
                "type": "update",
                "event_id": event_id,
                "market": market,
                "selection": selection,
                "fields": fields,
            }
        )

    @staticmethod
    def _find(records, event_id, market, selection):
        matches = [
            record
            for record in records
            if (record["event_id"], record["market"], record["selection"]) == (event_id, market, selection)
        ]
        if not matches:
            raise ValueError("aposta não encontrada")
        if len(matches) > 1:
            raise ValueError("múltiplas apostas para a mesma chave")
        return matches[0]

    @staticmethod
    def _validate_datetime(value, name):
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} deve ser datetime com timezone")
