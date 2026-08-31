"""Domain payload for ``sombra_diaria.py``; deliberately unaware of Scheduler."""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from predictor_ops.redaction import redact_text, sensitive_values

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "sombra_diaria.log"
# `pythonw.exe` (executavel de toda tarefa agendada) nao tem console: um
# processo de console filho ganharia janela VISIVEL na tela do dono.
# Saida ja e capturada, entao a flag nao esconde nada.
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

SENSITIVE_VALUES = sensitive_values(os.environ)

PASSOS = [
    (
        "odds_smoke",
        [
            sys.executable,
            "-X",
            "utf8",
            str(ROOT / "brasileirao_scripts" / "record_odds_smoke.py"),
            "--region",
            "eu",
        ],
        120,
    ),
    (
        "odds_stability",
        [sys.executable, "-X", "utf8", str(ROOT / "brasileirao_scripts" / "record_odds_smoke.py"), "--report"],
        60,
    ),
    ("ingest", [sys.executable, "-X", "utf8", "-m", "brasileirao_predictor.ingest_sofascore"], 5400),
    (
        "espelho",
        [sys.executable, "-X", "utf8", str(ROOT / "brasileirao_scripts" / "sync_matches_from_sofascore.py")],
        300,
    ),
    (
        "collection_only",
        [sys.executable, "-X", "utf8", str(ROOT / "brasileirao_scripts" / "collect_collection_only.py")],
        300,
    ),
    ("cron_models", [sys.executable, "-X", "utf8", "-m", "brasileirao_predictor.cron_update_models"], 600),
    (
        "settle",
        [sys.executable, "-X", "utf8", str(ROOT / "brasileirao_scripts" / "sombra.py"), "--settle"],
        300,
    ),
    (
        "capture",
        [sys.executable, "-X", "utf8", str(ROOT / "brasileirao_scripts" / "sombra.py"), "--capture"],
        300,
    ),
    (
        "report",
        [sys.executable, "-X", "utf8", str(ROOT / "brasileirao_scripts" / "sombra.py"), "--report"],
        120,
    ),
]


def log(msg: str) -> None:
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    linha = f"{stamp} {redact_text(msg, SENSITIVE_VALUES)}"
    print(linha, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def main() -> int:
    log("=== sombra_diaria: inicio ===")
    pior = 0
    for nome, cmd, timeout in PASSOS:
        try:
            r = subprocess.run(
                cmd,
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=_NO_WINDOW,
            )
            tail = (r.stdout or "").strip().splitlines()[-3:]
            for ln in tail:
                log(f"  [{nome}] {ln}")
            if r.returncode != 0:
                log(f"  [{nome}] FALHOU exit {r.returncode}: {(r.stderr or '').strip()[-300:]}")
                pior = max(pior, 1)
            else:
                log(f"  [{nome}] OK")
        except subprocess.TimeoutExpired:
            log(f"  [{nome}] TIMEOUT ({timeout}s) - passo abortado, sigo")
            pior = max(pior, 1)
        except Exception as e:
            log(f"  [{nome}] EXCECAO: {e}")
            pior = max(pior, 1)
    log(f"=== sombra_diaria: fim (exit {pior}) ===")
    return pior


if __name__ == "__main__":
    sys.exit(main())
