"""Rotina diária do modo SOMBRA (H3) — pensada para o Task Scheduler.

Sequência idempotente (segura para rodar 2x/dia, 10h e 23h):
  1. python -m src.ingest_sofascore        (odds novas + resultados novos)
  2. scripts/sync_matches_from_sofascore   (espelho → matches)
  3. python -m src.cron_update_models      (Elo + params de serving)
  4. scripts/sombra.py --settle            (liquida o que terminou)
  5. scripts/sombra.py --capture           (picks das fixtures com odds)
  6. scripts/sombra.py --report            (resumo no log)

Tudo com timeout e log em data/sombra_diaria.log (append) — a execução das
3h da manhã precisa ser investigável. Falha em um passo NÃO derruba os
seguintes (ingest fora do ar não pode impedir o settle do que já está no
banco), mas o exit code final reflete o pior resultado.

Agendamento (uma vez, PowerShell como usuário):
  schtasks /Create /TN "brasileirao-sombra-manha" /SC DAILY /ST 10:00 ^
    /TR "<python> -X utf8 <repo>\\scripts\\sombra_diaria.py"
  schtasks /Create /TN "brasileirao-sombra-noite" /SC DAILY /ST 23:00 ^
    /TR "<python> -X utf8 <repo>\\scripts\\sombra_diaria.py"
"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "sombra_diaria.log"

PASSOS = [
    ("ingest", [sys.executable, "-X", "utf8", "-m", "src.ingest_sofascore"], 5400),
    ("espelho", [sys.executable, "-X", "utf8",
                 str(ROOT / "scripts" / "sync_matches_from_sofascore.py")], 300),
    ("cron_models", [sys.executable, "-X", "utf8", "-m",
                     "src.cron_update_models"], 600),
    ("settle", [sys.executable, "-X", "utf8",
                str(ROOT / "scripts" / "sombra.py"), "--settle"], 300),
    ("capture", [sys.executable, "-X", "utf8",
                 str(ROOT / "scripts" / "sombra.py"), "--capture"], 300),
    ("report", [sys.executable, "-X", "utf8",
                str(ROOT / "scripts" / "sombra.py"), "--report"], 120),
]


def log(msg: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    linha = f"{stamp} {msg}"
    print(linha, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def main() -> int:
    log("=== sombra_diaria: inicio ===")
    pior = 0
    for nome, cmd, timeout in PASSOS:
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=timeout)
            tail = (r.stdout or "").strip().splitlines()[-3:]
            for ln in tail:
                log(f"  [{nome}] {ln}")
            if r.returncode != 0:
                log(f"  [{nome}] FALHOU exit {r.returncode}: "
                    f"{(r.stderr or '').strip()[-300:]}")
                pior = max(pior, 1)
            else:
                log(f"  [{nome}] OK")
        except subprocess.TimeoutExpired:
            log(f"  [{nome}] TIMEOUT ({timeout}s) — passo abortado, sigo")
            pior = max(pior, 1)
        except Exception as e:
            log(f"  [{nome}] EXCECAO: {e}")
            pior = max(pior, 1)
    log(f"=== sombra_diaria: fim (exit {pior}) ===")
    return pior


if __name__ == "__main__":
    sys.exit(main())
