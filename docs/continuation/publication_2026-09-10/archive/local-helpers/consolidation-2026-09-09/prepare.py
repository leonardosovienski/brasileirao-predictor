"""Copy known deliverables and preserve documentation snapshots; no application imports."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path('C:/BRASILEIRAO')
REPO = ROOT / 'brasileirao-predictor'
SOURCE = Path('C:/Users/leona/Documents/Codex/2026-09-09/le/outputs/BRASILEIRAO_PF_20260909')
DEST = ROOT / 'ENTREGAS/BRASILEIRAO_PF_20260909'
GIT = 'C:/Users/leona/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    DEST.mkdir(parents=True, exist_ok=False)
    receipt = []
    for source in sorted(SOURCE.rglob('*')):
        if source.is_symlink():
            raise ValueError('unexpected_link_in_delivery')
        if not source.is_file():
            continue
        relative = source.relative_to(SOURCE)
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if sha(source) != sha(target):
            raise ValueError('copy_mismatch')
        receipt.append({'source_relative': relative.as_posix(), 'sha256': sha(target), 'bytes': target.stat().st_size})
    originals = REPO / 'docs/history/antes_consolidacao_2026-09-09'
    originals.mkdir(parents=True)
    for relative in ('README.md', 'docs/continuation/RETOMADA.md', 'docs/continuation/PROMPT_MELHORIA_LUCRO.md',
                     'docs/DATA_MAP.md', 'docs/MIGRACAO_WINDOWS.md', 'docs/PROMPT_PROXIMA_SESSAO.md'):
        blob = subprocess.run([GIT, '-C', str(REPO), 'show', 'HEAD:' + relative], check=True, capture_output=True).stdout
        target = originals / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(blob)
    instructions = ROOT / 'INSTRUCOES'
    instructions.mkdir(exist_ok=True)
    attachment = Path('C:/Users/leona/.codex/attachments/1b8b841e-f67e-44c0-a1eb-96358b606fbf/pasted-text.txt')
    target = instructions / 'MANDATO_RECEBIDO_2026-09-09.txt'
    shutil.copy2(attachment, target)
    if sha(attachment) != sha(target):
        raise ValueError('instruction_copy_mismatch')
    text = attachment.read_text(encoding='utf-8-sig')
    header = ('> Mandato recebido em 09/09/2026. Raiz definida pelo usuário: **C:/BRASILEIRAO**.\n'
              '> Estado verificado e caminhos: [ESTADO_ATUAL.md](../ESTADO_ATUAL.md).\n'
              '> O corpo abaixo preserva o mandato; snapshots antigos são históricos.\n\n')
    (REPO / 'docs/continuation/MANDATO_LUCRO_2026-09-09.md').write_text(header + text, encoding='utf-8', newline='\n')
    result = {'status': 'PASS', 'copied_delivery_files': len(receipt), 'files': receipt,
              'instruction_sha256': sha(target), 'external_originals_deleted': False,
              'old_documentation_base': 'f33f92b37bd2c56cf0db978e7f5ad58d9cbae3ec'}
    (ROOT / 'AUDITORIA/consolidacao_copias_2026-09-09.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}))


if __name__ == '__main__':
    main()
