"""Index every project Markdown; inspect links only in explicitly current guides."""
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path('C:/BRASILEIRAO')
REPO = ROOT / 'brasileirao-predictor'
GIT = 'C:/Users/leona/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'
ACTIVE = {'README.md', 'HANDOFF.md', 'docs/ESTADO_ATUAL.md', 'docs/INDICE_DOCUMENTACAO.md',
          'docs/DATA_MAP.md', 'docs/MIGRACAO_WINDOWS.md', 'docs/PROMPT_PROXIMA_SESSAO.md',
          'docs/continuation/RETOMADA.md', 'docs/continuation/PROMPT_MELHORIA_LUCRO.md',
          'docs/continuation/MANDATO_LUCRO_2026-09-09.md'}
TOUCHED = ACTIVE | {'docs/ESTADO_LOCAL_E_OPERACAO.md', 'brasileirao_predictor/research/price_strength/README.md'}


def files():
    raw = subprocess.run([GIT, '-C', str(REPO), 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                         check=True, capture_output=True).stdout
    return sorted({name.decode('utf-8') for name in raw.split(b'\0') if name and name.lower().endswith(b'.md')})


def category(path):
    if path in ACTIVE or path == 'docs/continuation/MANDATO_LUCRO_2026-09-09.md':
        return 'Entrada e estado vigentes'
    if path.startswith('docs/history/'):
        return 'Versão anterior preservada integralmente'
    if path.startswith(('docs/experiments/', 'contracts/')) or re.search(r'(^|[/_])(A1|H14|H15|H9)([_/.]|$)', path):
        return 'Contrato ou referência protegida — preservar'
    if path.startswith(('docs/continuation/', 'docs/decisions/', 'docs/ou25_v2/', 'research/kimi_market05/')):
        return 'Histórico de pesquisa/implementação — preservar'
    if re.search(r'2026[-_]|RELATORIO|DOSSIE|AUDITORIA|ESTADO_LOCAL', path):
        return 'Relatório histórico — não é estado atual'
    return 'Referência técnica — não atesta operação local'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def links(path):
    # The checkpoint body is archived; only inspect the new checkpoint there.
    text = path.read_text(encoding='utf-8-sig')
    if path.name == 'HANDOFF.md':
        text = text.split('> ## CHECKPOINT — PREÇO EXECUTÁVEL', 1)[0]
    elif path.name == 'ESTADO_LOCAL_E_OPERACAO.md':
        text = text.split('Criado em 2026-09-06', 1)[0]
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    return [match.group(1).strip().strip('<>') for match in re.finditer(r'(?<!!)\[[^\]]*\]\(([^)]+)\)', text)]


def main():
    index_path = REPO / 'docs/INDICE_DOCUMENTACAO.md'
    index_path.touch(exist_ok=True)
    paths = files()
    grouped = Counter(category(path) for path in paths)
    output = ['# Índice da documentação — 09/09/2026', '',
              'O estado vigente está em [ESTADO_ATUAL.md](ESTADO_ATUAL.md).',
              'Todos os Markdown do checkout estão listados abaixo, inclusive os',
              'contratos e arquivos históricos. “Preservar” significa conservar',
              'protocolo, resultados e bytes; atualizar o índice não reabre estudos.', '',
              'Os Markdown da migração e das entregas foram inventariados por caminho',
              'e hash em `C:/BRASILEIRAO/AUDITORIA/markdown_fora_do_git.json`.',
              'Essas cópias históricas não são editadas ou executadas. Conteúdo de',
              'coortes protegidas não foi examinado para produzir este inventário.', '',
              '## Navegação', '',
              '- [Retomada](continuation/RETOMADA.md)',
              '- [Mandato vigente](continuation/MANDATO_LUCRO_2026-09-09.md)',
              '- [Mapa de dados e prefixos antigos](DATA_MAP.md)',
              '- [Migração verificada](MIGRACAO_WINDOWS.md)',
              '- [Último resultado econômico](continuation/price_feasibility_2026-09-09/RESULTADO.md)', '',
              f'## Inventário completo: {len(paths)} documentos', '',
              '| Documento | Categoria |', '| --- | --- |']
    for path in paths:
        relative = os.path.relpath(REPO / path, REPO / 'docs').replace('\\', '/')
        output.append(f'| [{path}]({relative}) | {category(path)} |')
    output += ['', 'As referências de estado da máquina antiga permanecem históricas.',
               'Quando um caminho antigo não existe, consulte DATA_MAP e o manifesto',
               'antes de adaptar um script. Não alterar documentos congelados para',
               'fazer um resultado antigo parecer produzido nesta instalação.', '']
    index_path.write_text('\n'.join(output), encoding='utf-8', newline='\n')
    missing, checked = [], 0
    for relative in sorted(TOUCHED):
        path = REPO / relative
        for link in links(path):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', link) or link.startswith('#'):
                continue
            local = unquote(link.split('#', 1)[0])
            target = (path.parent / local).resolve()
            checked += 1
            if not target.exists():
                missing.append({'document': relative, 'target': link})
    for link in links(ROOT / 'LEIA_PRIMEIRO.md'):
        if not (ROOT / link).resolve().exists():
            missing.append({'document': '../LEIA_PRIMEIRO.md', 'target': link})
        checked += 1
    frozen = []
    base = subprocess.run([GIT, '-C', str(REPO), 'ls-tree', '-r', '--name-only', 'f33f92b'],
                          check=True, capture_output=True).stdout.decode().splitlines()
    for path in base:
        if not path.endswith('.md') or path in TOUCHED:
            continue
        original = subprocess.run([GIT, '-C', str(REPO), 'show', 'f33f92b:' + path],
                                  check=True, capture_output=True).stdout
        actual = (REPO / path).read_bytes()
        # Working-tree eol may differ for ordinary text. Require exact bytes for
        # frozen archive paths; otherwise compare normalized text without rendering.
        exact = actual == original
        same = exact
        if not same:
            raise ValueError('preserved_markdown_changed:' + path)
        frozen.append({'path': path, 'sha256_working': hashlib.sha256(actual).hexdigest(),
                       'matches_git_content': same, 'exact_git_bytes': exact})
    snapshots = []
    for path in base:
        preserved = REPO / 'docs/history/antes_consolidacao_2026-09-09' / path
        if not preserved.is_file():
            continue
        original = subprocess.run([GIT, '-C', str(REPO), 'show', 'f33f92b:' + path],
                                  check=True, capture_output=True).stdout
        if preserved.read_bytes() != original:
            raise ValueError('historical_document_copy_changed')
        snapshots.append(path)
    inventory = [{'path': path, 'category': category(path), 'sha256': digest(REPO / path)} for path in paths]
    result = {'status': 'PASS' if not missing else 'FAIL', 'project_markdown_count': len(paths),
              'categories': dict(grouped), 'local_links_checked': checked, 'broken_active_links': missing,
              'preserved_existing_markdown_count': len(frozen), 'historical_copies_match_base': snapshots,
              'historical_link_bodies_not_rewritten': True, 'protected_outcomes_read': False,
              'inventory': inventory, 'preserved': frozen}
    (ROOT / 'AUDITORIA/markdown_projeto.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('inventory', 'preserved')}, ensure_ascii=False))
    if missing:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
