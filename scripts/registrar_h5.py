"""Pré-registro da H5: funil OU2.5 sombra com o ensemble atk/def-xG.

Por que um script separado do governanca.py: rodar o governanca.py de novo
re-registraria H1/H2 com sharpe=None — APAGANDO o sharpe observado 0.0722
da H1 (o "denominador imortal" do DSR). Este script registra SOMENTE a H5.

A trava de poder do core exige o atestado do harness
(data/trials.harness_attestation.json) para tentativa NOVA — o atestado
vigente cobre exatamente este funil (OU2.5, janela 2–15%, juiz PSR+IC):
a H5 muda a FONTE da probabilidade (ensemble), não o funil nem o juiz.

Uso: python scripts/registrar_h5.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from predictor_core.measurement.trials import TrialRegistry   # noqa: E402

TRIALS = ROOT / "data" / "trials.json"


def main():
    reg = TrialRegistry(TRIALS)
    reg.register(
        "h5-ensemble-xg-sombra-2026",
        params={
            "market": "ou25", "min_edge": 0.02, "max_edge": 0.15,
            "stake": "sombra-0u", "mode": "paper",
            "model": "ensemble 0.5·baseline(Elo+cosh) + 0.5·atkdef-xG "
                     "(w_xg=0.85, half_life=0.75a, ridge=1.0) — "
                     "src/xg_model.py, blend das grades de placar, "
                     "cache do cron_update_models",
            "captura": "scripts/sombra.py --capture — população paralela à "
                       "H3 (mesmos jogos, mesma janela, mesmas odds "
                       "correntes pré-apito), arquivos sombra_h5_*.jsonl",
            "league": "Brasileirão Série A", "season": "2026-returno",
        },
        sharpe=None,
        notes="H5: o ensemble validado em PREVISÃO no walk-forward 2025+2026 "
              "(docs/SIMULACAO_2025_2026.md: dBrier 1X2 −0,0073, IC95 "
              "[−0,0122, −0,0019], OU2.5 preservado) sustenta o funil OU2.5 "
              "em CLV/ROI ao vivo? Hiperparâmetros congelados pela validação "
              "2024-H2 ANTES de ver 2025/2026 — mudar blend/w_xg/half_life/"
              "ridge é tentativa N+1. DECISÃO com n≥100 picks liquidados "
              "(mesmo gate da H3): CLV médio IC95 (bootstrap cluster por "
              "jogo, 1000 iter, seed 13) > 0 E ROI IC_lower > −2% mantém a "
              "linha viva; senão, linha encerrada. Comparação pareada vs H3 "
              "nos jogos comuns é OBSERVACIONAL (mesma regra da "
              "estratificação da H3: não muda gatilho).",
        test_period=["2026-07-17", "2026-09-30"])
    errs = reg.validate()
    if errs:
        sys.exit("schema de trials violado: " + "; ".join(errs))
    trials = reg.load()
    print(f"pré-registro OK — {len(trials)} tentativa(s) em {TRIALS.name}")
    for t in trials:
        print(f"  - {t['name']} (registrada em {t['registered_at']}, "
              f"sharpe={t.get('sharpe')})")


if __name__ == "__main__":
    main()
