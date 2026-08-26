"""
paper_ledger.py — Ledger imutável de paper-trading com CLV.
Regras (herdadas do protocolo):
- toda aposta registrada ANTES do resultado ser conhecido (ts_capture < kickoff)
- flat stake sempre
- CLV obrigatório: odd de fechamento Pinnacle registrada ao fechar o mercado
- saída máxima: CAPITAL_GATE = LOCKED | ELIGIBLE_FOR_REVIEW (decisão humana)
"""
import json, os, hashlib
from datetime import datetime
import numpy as np
from bet_engine import sharpe_de_retornos, psr, dsr, roi_ic_bootstrap

class PaperLedger:
    def __init__(self, path="paper_ledger.jsonl", trials_declarados=10, gate_dsr=0.95):
        self.path = path
        self.trials = trials_declarados   # declarar ex ante; alimenta o DSR
        self.gate = gate_dsr

    def registrar_aposta(self, event_id, market, selection, book, odd, ts_capture,
                         kickoff, stake=1.0):
        assert ts_capture < kickoff, "VIOLAÇÃO PIT: aposta registrada após kickoff"
        rec = {"type": "bet", "event_id": event_id, "market": market,
               "selection": selection, "book": book, "odd": odd,
               "ts_capture": ts_capture.isoformat(), "kickoff": kickoff.isoformat(),
               "stake": stake, "closing_odd": None, "result": None, "ret": None}
        self._append(rec)
        return rec

    def registrar_fechamento(self, event_id, market, selection, closing_odd):
        """Atualiza o registro com a odd de fechamento Pinnacle (base do CLV)."""
        self._update(event_id, market, selection, {"closing_odd": closing_odd})

    def liquidar(self, event_id, market, selection, acertou):
        recs = self._load()
        for r in recs:
            if (r["event_id"], r["market"], r["selection"]) == (event_id, market, selection):
                assert r["closing_odd"] is not None, "liquidar sem closing_odd (CLV) é proibido"
        ret = None
        self._update(event_id, market, selection, {
            "result": "win" if acertou else "loss",
            "ret": None})  # ret calculado abaixo
        recs = self._load()
        for r in recs:
            if (r["event_id"], r["market"], r["selection"]) == (event_id, market, selection):
                r["ret"] = (r["odd"] - 1) * r["stake"] if acertou else -r["stake"]
        self._save(recs)

    def relatorio(self):
        recs = [r for r in self._load() if r.get("ret") is not None]
        if len(recs) < 2:
            return {"status": "insuficiente", "n": len(recs)}
        rets = np.array([r["ret"] for r in recs])
        clvs = np.array([r["odd"]/r["closing_odd"] - 1 for r in recs])
        roi, ic = roi_ic_bootstrap(rets)
        from scipy import stats as st
        sk, ku = float(st.skew(rets)), float(st.kurtosis(rets)+3)
        sr = sharpe_de_retornos(rets)
        d = dsr(self.trials, sr, len(rets), sk, ku)
        return {
            "n": len(recs),
            "roi": round(roi, 4), "roi_ic95": [round(x,4) for x in ic],
            "clv_medio": round(float(clvs.mean()), 4),
            "clv_pct_positivo": round(float((clvs > 0).mean()), 4),
            "sharpe": round(sr, 4), "psr": round(psr(sr,0,len(rets),sk,ku), 4),
            "dsr": round(d, 4),
            "CAPITAL_GATE": "ELIGIBLE_FOR_REVIEW" if (d >= self.gate and clvs.mean() > 0
                            and ic[0] > 0) else "LOCKED",
        }

    def _append(self, rec):
        rec["hash_prev"] = self._last_hash()
        line = json.dumps(rec)
        with open(self.path, "a") as f:
            f.write(line + "\n")

    def _last_hash(self):
        if not os.path.exists(self.path): return "GENESIS"
        with open(self.path) as f:
            lines = f.read().strip().split("\n")
        return hashlib.sha256(lines[-1].encode()).hexdigest()[:16] if lines and lines[0] else "GENESIS"

    def _load(self):
        if not os.path.exists(self.path): return []
        return [json.loads(l) for l in open(self.path) if l.strip()]

    def _update(self, event_id, market, selection, fields):
        recs = self._load()
        for r in recs:
            if (r["event_id"], r["market"], r["selection"]) == (event_id, market, selection):
                r.update(fields)
        self._save(recs)

    def _save(self, recs):
        with open(self.path, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
