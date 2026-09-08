"""Preserve the internal review and reconcile explicitly allowed source changes.

Standard library only; no imports from the application or evaluation runners.
Does not rerun studies, inspect provider data semantically, or rewrite old locks.
"""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
ARCHIVES = Path('C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07')
OUT = ROOT / 'outputs/REVISAO_DO_CHAT'
DOCS = REPO / 'docs/continuation/whole_chat_review_2026-09-08'
BACKUP = ARCHIVES / 'whole_chat_review_2026-09-08'
CHANGED = {
    'brasileirao_predictor/research/price_strength/quotes.py': '31e04a5b5739e1f13aa8c3339a0bb527dc3616decb2697aa9995ce69e0ee8889',
    'brasileirao_predictor/research/price_strength/study.py': 'ff513cada2f69394a89c5d3067a952a556f71f036ce978124d8de54a4d7da998',
    'brasileirao_predictor/research/price_strength/__main__.py': '6d65c28142f583a1cf2aaa1be17e52f1fefa1253c67eea2f9ab3554dd3040119',
    'brasileirao_predictor/research/price_strength/dynamic_xg.py': 'e780a459b08dd778877ceddb029fbc2855d02490b692a3bd456239754ba75d06',
    'tests/test_price_strength_review_regressions.py': '30d482f625597399e851dc135094b9f61a2797a57f20090c7d1b6100361e57de',
}
REQUIRED_RECEIPTS = [
    'research_review_targeted_pytest', 'research_review_regressions_final',
    'research_review_lint_final', 'research_review_format_final',
    'research_review_pyright_final', 'whole_chat_runtime_characterization',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert sha(source) == sha(target), str(target)


assert not BACKUP.exists(), 'Do not overwrite a completed review archive'
assert not DOCS.exists(), 'Do not overwrite a completed review document set'
before = read(OUT / 'evidence_check.json')
assert before['status'] == 'PASS'
old_sources = {name: item['actual'] for name, item in before['current_sources'].items()}
assert len(set(old_sources) & set(CHANGED)) == 4
source_hashes = {name: sha(REPO / name) for name in old_sources | CHANGED}
for name, digest in source_hashes.items():
    assert digest == CHANGED.get(name, old_sources.get(name)), name
for name, digest in CHANGED.items():
    assert sha(ROOT / 'work/integration-repo' / name) == digest, name

protected_expected = read(ROOT / 'outputs/MELHORIA_RUNTIME/estado.json')['protected_sha256']
protected_checks = {name: sha(REPO / name) == digest for name, digest in protected_expected.items()}
assert len(protected_checks) == 14 and all(protected_checks.values())
old_archives = []
for item in before['backup_manifests']:
    folder = ARCHIVES if item['archive'] == 'initial_477' else ARCHIVES / item['archive']
    manifest = folder / 'BACKUP_MANIFEST.json'
    assert sha(manifest) == item['manifest_sha256']
    entries = read(manifest)['files']
    for entry in entries:
        target = (folder / entry['path']).resolve()
        assert target.is_relative_to(folder.resolve())
        assert sha(target) == entry['sha256'], str(target)
    old_archives.append({**item, 'verified_after_patch': True})

studies = {}
for name, directory in [('TESTE_XG_REAL', OUT.parent / 'TESTE_XG_REAL'),
                        ('CORRECAO', OUT.parent / 'DIAGNOSTICO_XG/CORRECAO')]:
    manifest_path = directory / 'MANIFEST.json'
    assert sha(manifest_path) == before['study_manifests'][name]['manifest_sha256']
    for relative, digest in read(manifest_path)['files'].items():
        assert sha(directory / relative) == digest, relative
    studies[name] = {**before['study_manifests'][name], 'verified_after_patch': True}
for name, item in before['previous_helpers'].items():
    assert sha(ROOT / 'work/price_strength_evaluation' / name) == item['current_sha256']

receipt_results = {}
for name in REQUIRED_RECEIPTS:
    path = ROOT / 'work/validation' / (name + '.json')
    receipt = read(path)
    assert receipt['exit_code'] == 0, name
    receipt_results[name] = {'exit_code': 0, 'receipt_sha256': sha(path), 'command': receipt['command']}
pyright_log = (ROOT / 'work/validation/research_review_pyright_final.log').read_text(encoding='utf-8-sig')
assert 'Total files checked: 8' in pyright_log and '0 errors, 0 warnings' in pyright_log

for name in ['CODE_REVIEW.md', 'METHODOLOGY_REVIEW.md', 'RESEARCH_CODE_REVIEW.md']:
    copy(ROOT / 'work/whole_chat_review' / name, OUT / name)
for pattern in ['research_review_*', 'research_adversarial_regressions.*', 'whole_chat_runtime_characterization.*']:
    for source in (ROOT / 'work/validation').glob(pattern):
        if source.is_file():
            copy(source, OUT / 'validation' / source.name)

state = {
    'verified_at_utc': datetime.now(UTC).isoformat(),
    'review': 'Five completed turns plus available current-turn evidence; internal review, not an external audit.',
    'status': 'REVIEW_COMPLETE_WITH_RESIDUAL_RUNTIME_AND_ECONOMIC_LIMITS',
    'source_sha256': source_hashes,
    'changed_in_this_review_sha256': CHANGED,
    'unchanged_previous_source_count': len(old_sources) - 4,
    'protected_sha256': protected_expected,
    'protected_checks': protected_checks,
    'previous_backup_manifests': old_archives,
    'previous_archived_files_verified': sum(item['files'] for item in old_archives),
    'closed_studies': studies,
    'transitive_helper_retrospective_evidence': before['previous_helpers'],
    'transitive_helper_limit': 'evaluate.py was omitted from correction plan/lock. Old bytes match earlier archive; original plan and lock have not been amended.',
    'validation_receipts': receipt_results,
    'validation_counts': {
        'targeted_pytest_passed': 230, 'windows_symlink_skipped': 1,
        'new_regression_cases_in_targeted_suite': 16,
        'affected_tests_after_last_typing_change_passed': 30,
        'runtime_characterization_cases_reproducing_unfixed_limitations': 2,
        'pyright_sources_checked': 8,
    },
    'discarded_validation': 'Pyright with project exclusions checked zero source files; not an approval. Intermediate typing error corrected before final scoped check.',
    'research_config_unchanged': True,
    'research_formulas_unchanged': True,
    'new_economic_fit_or_backtest': False,
    'latest_closed_result': {'fixtures': 362, 'bets': 170, 'net_units': -23.373, 'roi_percent_rounded': -13.75, 'profitability_established': False},
    'remaining_limits': [
        'Older runtime response may overwrite newer state; no current-run sequencing across producer/consumer.',
        'Failure after NX claim may suppress immediate retry until 60-second TTL.',
        'Redis-dependent Python test, 13 WorkerRuntime tests and Compose E2E not executed.',
        '2025 already inspected; adaptive exploration is not independent validation.',
        'Retrospective odds and assumed xG publication lag do not attest executable prices or availability.',
    ],
    'persistent_docs': str(DOCS), 'persistent_backup': str(BACKUP),
    'commit_or_push': False, 'live_database_access': False, 'financial_actions': False,
}
write_json(OUT / 'estado.json', state)

handoff = REPO / 'HANDOFF.md'
handoff_body = handoff.read_text(encoding='utf-8-sig')
heading, remainder = handoff_body.split('\n', 1)
checkpoint = '''
> ## CHECKPOINT — REVISÃO DO CHAT COMPLETO (08/09/2026 UTC)
>
> As cinco etapas anteriores foram relidas; julgamento e evidências em
> docs/continuation/whole_chat_review_2026-09-08/RESULTADO.md e estado.json.
> Manter reparos de integridade e resultados negativos. Refazer a sequência
> com qualidade/proveniência dos dados antes do modelo; os zeros de 2021
> deveriam ter sido investigados antes do primeiro replay. 2025 continua
> exploratório/adaptativo. “Auditoria independente” anterior significa
> verificação interna por implementação separada da mesma equipe.
>
> Quatro bugs adicionais de pesquisa corrigidos: duplicação de identidade
> do provedor, elegibilidade truthy indevida, kickoff de quote futura
> interferindo no passado e erro CLI ecoando entrada. 16 regressões novas;
> 230 testes passaram/1 symlink pulado; após ajuste de tipagem, 30 afetados
> passaram novamente. Ruff/formato e Pyright com 8 fontes passaram.
> Fórmulas, configuração, runner condicional e saldos fechados preservados.
>
> Dois testes sintéticos reproduziram limitações NÃO corrigidas do runtime:
> resposta antiga pode sobrescrever nova; falha após claim suprime retry
> imediato por até 60s. Correlação de IDs não garante versão atual.
> Redis/Compose continua pendente; não declarar prontidão de operação.
>
> Gap documental: evaluate.py importado pela correção não constou do lock
> transitivo. Hash atual igual ao backup anterior, conciliação retrospectiva;
> não reescrever o plano/lock para aparentar congelamento prévio completo.
> 764 arquivos antigos, 14 protegidos e estudos fechados reconferidos.
> Nova cópia: brasileirao-predictor-sessoes/2026-09-07/
> whole_chat_review_2026-09-08/. Último saldo continua −23,373u/170 apostas,
> ROI −13,75%; ganho vs raw vem de custos menores, com ROI pior.
> Sem novo backtest/fit, coleta, banco operacional, capital, coorte/agenda,
> commit ou push. Revisão encerrada; rentabilidade não demonstrada.

'''
handoff.write_text(heading + '\n' + checkpoint + remainder, encoding='utf-8')
retomada = REPO / 'docs/continuation/RETOMADA.md'
retomada_body = retomada.read_text(encoding='utf-8-sig')
heading, remainder = retomada_body.split('\n', 1)
retomada_note = '''
> Etapa mais recente: [revisão do chat completo](whole_chat_review_2026-09-08/RESULTADO.md).
> Quatro falhas de pesquisa corrigidas; 230 testes passaram/1 skip; Ruff e Pyright
> dirigidos passaram. Duas limitações do runtime foram reproduzidas e permanecem
> pendentes, junto de Redis/Compose. Nenhum novo backtest ou resultado econômico.
> Auditoria dos dados deveria preceder a modelagem; 2025 segue exploratório;
> verificações anteriores foram internas por implementações separadas.
> Ler o primeiro checkpoint do HANDOFF e o estado desta revisão.

'''
retomada.write_text(heading + '\n' + retomada_note + remainder, encoding='utf-8')

for source in OUT.rglob('*'):
    if source.is_file():
        copy(source, DOCS / source.relative_to(OUT))
for name in ['test_research_adversarial.py', 'test_runtime_characterization.py', 'verify_evidence.py', 'preserve_review.py']:
    copy(ROOT / 'work/whole_chat_review' / name, DOCS / 'reproducao' / name)
for relative in ['work/validation_runner.py', 'work/guard/sitecustomize.py', 'work/price_strength_pyright.json']:
    source = ROOT / relative
    copy(source, DOCS / 'reproducao' / relative)

for source in OUT.rglob('*'):
    if source.is_file():
        copy(source, BACKUP / 'outputs/REVISAO_DO_CHAT' / source.relative_to(OUT))
for source in (ROOT / 'work/whole_chat_review').iterdir():
    if source.is_file():
        copy(source, BACKUP / 'work/whole_chat_review' / source.name)
for relative in ['work/validation_runner.py', 'work/guard/sitecustomize.py', 'work/price_strength_pyright.json']:
    copy(ROOT / relative, BACKUP / relative)
for relative in CHANGED:
    copy(REPO / relative, BACKUP / 'code' / relative)
for relative in ['HANDOFF.md', 'docs/continuation/RETOMADA.md']:
    copy(REPO / relative, BACKUP / 'code' / relative)

entries = [{'path': str(path.relative_to(BACKUP)).replace('\\', '/'), 'bytes': path.stat().st_size, 'sha256': sha(path)}
           for path in sorted(BACKUP.rglob('*')) if path.is_file()]
write_json(BACKUP / 'BACKUP_MANIFEST.json', {
    'created_at_utc': datetime.now(UTC).isoformat(),
    'scope': 'Internal whole-chat review, new synthetic regressions, receipts and changed source snapshots. No original files removed.',
    'files': entries,
})
for item in entries:
    assert sha(BACKUP / item['path']) == item['sha256']
receipt = {
    'created_at_utc': datetime.now(UTC).isoformat(),
    'backup': str(BACKUP), 'files': len(entries),
    'total_bytes': sum(item['bytes'] for item in entries),
    'manifest_sha256': sha(BACKUP / 'BACKUP_MANIFEST.json'),
    'all_copies_verified': True,
    'receipt_location_note': 'Receipt is outside the manifest to avoid a circular hash dependency.',
}
write_json(OUT / 'backup_receipt.json', receipt)
copy(OUT / 'backup_receipt.json', DOCS / 'backup_receipt.json')
print(json.dumps({'status': 'PASS', 'old_backup_files': 764, 'protected': 14,
                  'current_sources': len(source_hashes), 'new_backup': receipt}, ensure_ascii=False, indent=2))
