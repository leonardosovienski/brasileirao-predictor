"""Persist public-source research, without touching operational datasets."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import shutil

workspace = Path(__file__).resolve().parent.parent
repo = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
output = workspace / 'outputs/PESQUISA_MODELOS'
destination = repo / 'docs/continuation/model_research_2026-09-07'
backup = Path('C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07/model_research_2026-09-07')
report = output / 'PESQUISA.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


reference = json.loads((repo / 'docs/continuation/review_2026-09-07/estado_final.json').read_text(encoding='utf-8'))
checks = {name: sha(repo / name) == value for name, value in reference['protected_sha256'].items()}
assert all(checks.values()), 'Protected file hash mismatch'
urls = sorted(set(re.findall(r'\]\((https://[^\s)]+)\)', report.read_text(encoding='utf-8'))))
state = {
    'created_at_utc': datetime.now(UTC).isoformat(),
    'request': 'Pesquisar ideias e modelos semelhantes e explicar como apresentam lucro.',
    'method': 'Leitura de fontes primárias, artigos e código público; síntese crítica e comparação com o diagnóstico preservado.',
    'report_sha256': sha(report),
    'source_urls': urls,
    'external_backtests_reproduced': False,
    'operational_changes': False,
    'new_candidate_validated': False,
    'protected_hash_checks': checks,
    'validation': 'Relatório revisado; 14 hashes protegidos conferidos. Sem testes adicionais de código nesta etapa documental.',
    'economic_conclusion': 'Lucro realizável do projeto continua não demonstrado.',
    'pending_from_previous_stage': 'Integrações Redis e Compose E2E; alterações de runtime locais sem commit/push.',
    'persistence_command': '.venv/Scripts/python.exe <workspace>/work/persist_model_research.py',
}
write_json(output / 'estado.json', state)
destination.mkdir(parents=True, exist_ok=True)
backup.mkdir(parents=True, exist_ok=True)
sources = []
for name in ['PESQUISA.md', 'estado.json']:
    shutil.copy2(output / name, destination / name)
    sources.append((destination / name, name))
sources.extend([
    (repo / 'HANDOFF.md', 'HANDOFF_snapshot.md'),
    (repo / 'docs/continuation/RETOMADA.md', 'RETOMADA_snapshot.md'),
    (Path(__file__), 'persist_model_research.py'),
])
entries = []
for source, name in sources:
    target = backup / name
    shutil.copy2(source, target)
    assert sha(source) == sha(target)
    entries.append({'path': name, 'bytes': target.stat().st_size, 'sha256': sha(target)})
manifest = {'created_at_utc': datetime.now(UTC).isoformat(), 'files': entries}
write_json(backup / 'BACKUP_MANIFEST.json', manifest)
assert sha(report) == sha(destination / report.name) == sha(backup / report.name)
print(json.dumps({'protected_files_verified': len(checks), 'source_urls': len(urls),
                  'backup_files_verified': len(entries), 'report_sha256': sha(report),
                  'report': str(report), 'persistent_copy': str(destination),
                  'backup': str(backup)}, ensure_ascii=False, indent=2))
