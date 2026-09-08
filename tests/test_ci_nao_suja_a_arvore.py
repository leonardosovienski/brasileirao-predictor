"""O CI não pode sujar a própria árvore de trabalho.

Achado 7 da auditoria adversarial de 2026-09-05, segunda ordem. O core 3.2.0
recusa emitir atestado de poder a partir de árvore suja, porque um atestado
cujo `code_version` termina em `;dirty` destrava trials que ninguém consegue
reproduzir.

Isso torna a limpeza da árvore uma propriedade do PIPELINE, não só do
desenvolvedor: se um passo do CI escreve um artefato não ignorado, todo passo
posterior que emita atestado passa a produzir `;dirty` — ou a falhar. Foi o que
aconteceu com `wheelhouse/`, onde o passo "Verify canonical shared wheel
hashes" baixa as wheels canônicas: faltava no .gitignore, a árvore do runner
ficava suja durante o pytest inteiro, e ninguém via porque o core 3.1.0 não
olhava. O gate não criou o problema; expôs um que já existia.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Diretórios em que o ci.yml escreve durante a run, antes ou junto do pytest.
ARTEFATOS_DO_CI = ("wheelhouse", ".wheelhouse-e2e", "dist", "artifacts")


def _ignorado(caminho: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", caminho], cwd=ROOT, capture_output=True).returncode == 0


def test_todo_diretorio_de_artefato_do_ci_esta_ignorado() -> None:
    nao_ignorados = [d for d in ARTEFATOS_DO_CI if not _ignorado(f"{d}/x")]
    assert not nao_ignorados, (
        f"{nao_ignorados} não estão no .gitignore. O CI escreve neles durante a run, "
        "então a árvore fica suja e a emissão de atestado passa a produzir "
        "code_version com ';dirty' — ou a falhar com DirtyWorkingTreeError."
    )


def test_a_lista_cobre_todo_destino_de_download_do_workflow() -> None:
    """Guarda contra a lista acima envelhecer.

    Se alguém acrescentar um `--output outro_dir/...` no ci.yml, este teste
    falha até que o diretório entre na lista — e o teste de cima então exige
    que ele esteja ignorado.
    """
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    destinos = {m.split("/", 1)[0] for m in re.findall(r"--output\s+([\w.\-/]+)", workflow) if "/" in m}
    fora_da_lista = destinos - set(ARTEFATOS_DO_CI)
    assert not fora_da_lista, (
        f"o ci.yml baixa para {sorted(fora_da_lista)}, que não está em "
        "ARTEFATOS_DO_CI; acrescente lá e garanta que esteja no .gitignore"
    )
