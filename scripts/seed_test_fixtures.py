#!/usr/bin/env python3
"""Gera o artefato operacional SINTÉTICO que a suíte precisa num clone limpo.

`data/matches.db` nasce do pipeline de ingestão (Sofascore/FBref) e está no
`.gitignore` (`*.db`). Num runner de CI ele nunca existe, e
`tests/test_operational_provenance.py` depende dele: `consumer_provenance()`
hasheia o arquivo para carimbar a proveniência do envelope operacional.
Historicamente isso era "resolvido" com `|| true` no workflow, que forçava exit
0 e apagava junto qualquer regressão real do resto da suíte.

O banco é criado VAZIO, com o schema canônico — `src.db.connect` já executa o
DDL, então o schema não é duplicado aqui e não pode divergir do real. Vazio
basta: o teste hasheia o arquivo, não consulta linhas. Nada aqui fabrica
resultado de jogo; um banco com partidas inventadas seria pior que um vazio,
porque poderia fazer um teste de modelo passar por acidente.

REGRA DE SEGURANÇA: nunca sobrescreve arquivo existente. Na máquina do operador
o `matches.db` real é dado de ingestão — perdê-lo por rodar um script de teste
seria inaceitável. Sem `--force`, um arquivo já presente é preservado.

Uso:
    python scripts/seed_test_fixtures.py           # cria só o que falta
    python scripts/seed_test_fixtures.py --force   # recria (DESTRUTIVO)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "matches.db"


def build_database(path: Path) -> None:
    """Cria o banco vazio com o schema canônico de `src.db`."""
    sys.path.insert(0, str(ROOT))
    from src.db import connect  # importado aqui: precisa do ROOT no sys.path

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(str(path))
    try:
        conn.commit()
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="recria mesmo se o arquivo já existir (DESTRUTIVO)")
    args = parser.parse_args(argv)

    if DB_PATH.exists() and not args.force:
        print(f"preservado (já existe): {DB_PATH.relative_to(ROOT)}")
        return 0
    build_database(DB_PATH)
    print(f"gerado: {DB_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
