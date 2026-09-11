"""Verify immutable receipts, byte boundaries and explicit paths before staging."""
import hashlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
docs=repo/'docs/continuation/closeout_2026-09-10';ev=docs/'evidence'
base='9b8cde83f40565278375d343b658afaa385e235e'
def git(*args):return subprocess.check_output(['git',*args],cwd=repo).decode('utf-8').strip()
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert git('rev-parse','HEAD')==base and git('branch','--show-current')=='main'
quality=json.loads((root/'quality-checks-final.json').read_text())
assert all(r['exit_code']==0 for r in quality['commands'])
package=json.loads((root/'package-receipt-final.json').read_text())
assert len(package['commands'])==7 and all(r['exit_code']==r['expected'] for r in package['commands'])
assert '--python' in package['commands'][1]['argv']
summary=json.loads((ev/'validation-summary.json').read_text())
assert summary['python_passed']==275 and summary['dotnet_passed']==127 and summary['dotnet_failed']==0
for name in ('runtime','latency-before','latency-after'):
    assert json.loads((root/name/'receipt.json').read_text())['server_stopped']
shutil.copyfile(root/'package-receipt-final.json',ev/'package-receipt-final.json')
for source in (root/'package-smoke-final').glob('*.log'):
    dest=ev/'package-smoke-final'/source.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(source,dest)
dump(ev/'automation-config-attempt.json',dict(verified_at=datetime.now(UTC).isoformat(),
    inspected='C:/Users/leona/.codex/automations/completar-dados-do-brasileir-o/automation.toml',
    exists=False,interpretation='Expected local TOML absent; does not prove absence of the app heartbeat. Prior view only rendered a card.',
    automation_modified=False,active_execution_verified=False))
(docs/'NOTAS_DE_VERIFICACAO.md').write_text('''# Notas finais de verificação CLO

Regressões Python anteriores: before32 falhas/1 passagem, coverage-before2 falhas, status-before1, research-before16. Depois, integrated-final275 passagens, sem falhas/skips. Guard bloqueou uma tentativa socket.bind antes de acesso; nenhuma tentativa de SQLite operacional no lote final após retirar o CLV automático.

Ruff/Pyright primeiro encontraram linhas longas e acesso Optional no teste; falhas preservadas em quality-first. Correções sem exclusões/tolerâncias novas. Última verificação14 arquivos Python, zero erros/avisos. Testes antigos de readiness atualizados para a versão2, que retira selo oficial; teste de closing ganhou contexto de fonte/evento/período/status exigido pela versão2.

.NET: runtime119/119; latency-before119 passagens e6 novas regressões falharam; latency-after127/127. Os3 testes de configuração de budget foram movidos para classe sem fixture Redis porque não precisam de conexão; as3 mesmas entradas inválidas continuam testadas. Dois testes adicionais verificam CAS obsoleto e revisão com clocks inválidos. Namespace de estatísticasv2 preserva o v1. Não foram aumentados timeouts para fazer testes passar. Falha de bootstrap anterior permanece no checkpoint CPL; causa ainda desconhecida.

Pacote: wheel e sdist offline, instalação com --python apontado explicitamente ao RI. Sete comandos e validação de saídas/códigos de retorno. Nenhuma autodetecção de outro projeto nesta etapa. A wheel contém Python e scripts; .NET é fonte/bundle com build/test isolado comprovado. Notas, manifestos e recibo final são produzidos depois do build e entregues separadamente; não alegar que estão dentro do sdist.

Automação: ferramenta view antes retornou apenas cartão. Tentativa somente leitura do TOML esperado não encontrou arquivo; isso não prova que o heartbeat do aplicativo foi removido ou esteja inativo. Nenhum agendamento alterado/duplicado. A execução futura só pode ser afirmada com recibo e estado apropriados.

Esta é uma integração de continuidade, com mandato_complete=false. Sem novas métricas de mercado, preços, labels ou operações financeiras. Campos de retencão/latência são diagnóstico técnico. JSON/XML/logs de máquinas são preservados byte a byte; o .gitattributes local permite o espaço bruto do runner e evita normalização desses recibos.
''',encoding='utf-8')
for name in ['REGISTROS.md','REGISTROS.json','PROXIMO_PROMPT.md']:
    path=docs/name
    text=path.read_text(encoding='utf-8').replace('gols fracionários e recibo','contagens de jogos fracionárias e recibo').replace('preserves51','preserve as51')
    path.write_text(text,encoding='utf-8')
next_prompt=Path('C:/BRASILEIRAO/INSTRUCOES/PROXIMO_PROMPT_APOS_VERIFICACAO_ADICIONAL_2026-09-10.md')
next_prompt.write_text((docs/'PROXIMO_PROMPT.md').read_text(encoding='utf-8'),encoding='utf-8')
changes=git('diff','HEAD','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()
assert all(p.startswith(('brasileirao_predictor/','tests/','dotnet/','docs/continuation/closeout_2026-09-10/')) or p in {
    'README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md'} for p in changes)
inventory=json.loads((ev/'source-inventory.json').read_text())
protected={r['path'] for r in inventory if r['review'].startswith('protected')}
frozen=json.loads((ev/'boundary-check.json').read_text())['preserved_shared_or_frozen_files']
assert not set(changes)&(protected|set(frozen))
for name in changes:
    path=repo/name
    if not path.is_file():continue
    assert '.env' not in path.parts
    raw=path.read_bytes()
    assert not any(re.search(p,raw) for p in [rb'ghp_[A-Za-z0-9]{30,}',rb'sk-(?:proj-)?[A-Za-z0-9_-]{40,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']),name
files={}
for path in sorted(docs.rglob('*')):
    if path.is_file() and path.name!='manifest.json':
        raw=path.read_bytes();files[path.relative_to(docs).as_posix()]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
dump(ev/'manifest.json',dict(round='CLO-20260910',base=base,files=files))
subprocess.run(['git','diff','--check'],cwd=repo,check=True)
(root/'precommit.diff').write_bytes(subprocess.check_output(['git','diff','HEAD','--binary'],cwd=repo))
changes=sorted(set(git('diff','HEAD','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()))
dump(root/'staged-paths.json',changes)
subprocess.run(['git','add','--',*changes],cwd=repo,check=True)
subprocess.run(['git','diff','--cached','--check'],cwd=repo,check=True)
print(json.dumps(dict(staged_files=len(changes),evidence_files=len(files),base=base,ready_for_checkpoint_commit=True)))
