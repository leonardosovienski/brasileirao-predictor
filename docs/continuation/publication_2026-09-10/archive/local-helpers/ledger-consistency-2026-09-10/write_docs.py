"""Publish dated LGC evidence without modifying frozen prior reports."""
import collections
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
base = Path('C:/BRASILEIRAO')
repo = base / 'brasileirao-predictor'
docs = repo / 'docs/continuation/ledger_consistency_2026-09-10'
prior = repo / 'docs/continuation/closeout_2026-09-10'
sha = 'c2fd45675cf84cf6ba4ed637a111eaf5d6ba74ac'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() == sha
docs.mkdir(exist_ok=False)
evidence = docs / 'evidence'
evidence.mkdir()

def write(path, value):
    path.write_text(value, encoding='utf-8')

def dump(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def hash_file(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

paths = [f'{phase}/{name}' for phase in ('before', 'after', 'final') for name in ('junit.xml', 'isolation.json')]
paths += ['process-lab/failure.json', 'process-lab-v2/receipt.json', 'quality-checks-final.json',
          'pyright-final.log', 'ruff-fix-final.log', 'ruff-format-final.log', 'ruff-check-final.log',
          'ruff-format-check-final.log', 'package-receipt-final.json']
paths += [p.relative_to(root).as_posix() for p in (root / 'package-smoke-final').glob('*.log')]
for name in paths:
    target = evidence / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, target)
    assert hash_file(root / name) == hash_file(target)
shutil.copyfile(prior / 'evidence/.gitattributes', evidence / '.gitattributes')
shutil.copyfile(root / 'PLANO.md', docs / 'PLANO.md')
counts = {}
for phase in ('before', 'after', 'final'):
    suite = ET.parse(root / phase / 'junit.xml').getroot()
    cases = list(suite.iter('testcase'))
    counts[phase] = dict(tests=len(cases), failures=sum(c.find('failure') is not None for c in cases),
                         errors=sum(c.find('error') is not None for c in cases),
                         skipped=sum(c.find('skipped') is not None for c in cases))
assert counts['before'] == dict(tests=23, failures=21, errors=0, skipped=0)
assert counts['final'] == dict(tests=95, failures=0, errors=0, skipped=0)
quality = json.loads((root / 'quality-checks-final.json').read_text())
assert all(c['exit_code'] == 0 for c in quality['commands'])
lab = json.loads((root / 'process-lab-v2/receipt.json').read_text())
assert lab['holder_stopped'] and lab['lock_source_sha256'] == hash_file(repo / 'brasileirao_predictor/bet_log.py')['sha256']
dump(evidence / 'validation-summary.json', dict(python=counts, quality_passed=True,
     os_lock_verified='Windows local filesystem; threads and separate processes; abrupt owned child exit releases lock',
     posix_lock_executed=False, new_dotnet_or_redis_run=False, protected_evaluation=False,
     operational_data_access=False, economic_performance_experiment=False))

registry = json.loads((prior / 'REGISTROS.json').read_text(encoding='utf-8'))
registry.update(round='LGC-20260910', dated_at=datetime.now(UTC).isoformat(), base=sha,
                previous_registry='../closeout_2026-09-10/REGISTROS.json', mandate_complete=False)
items = [
    ('Escritores concorrentes preservam unicidade e bytes válidos',
     'Leitura seguida de append sem exclusão permitia duplicar ID e liquidação; última linha sem LF era concatenada.',
     'Trava de SO por caminho canônico, não bloqueante, em sidecar persistente; append preserva bytes, acrescenta separador se necessário, flush e fsync.',
     'before: duas concorrências e linha sem LF falham; final: passam; process-lab-v2 prova exclusão e liberação após encerramento abrupto do filho próprio.',
     'Escritores cooperantes, mesmo caminho e filesystem local Windows. POSIX implementado, não executado. Sem transação entre livros, sem garantia contra edição externa ou falha parcial de disco.'),
    ('Saldo manual usa um snapshot reconciliado e valores bancários válidos',
     'Duas leituras combinavam lucro antigo com exposição nova; JSON bancário aceitava NaN, booleanos, negativos, campos repetidos e relógios sem timezone.',
     'Uma leitura de apostas antes de filtrar/somar; parser estrito compartilhado, domínios bancários e clocks explícitos; gravações bancárias usam a mesma trava.',
     'before: snapshot e oito casos bancários falham; final: passam; 95 testes finais cobrem liquidação, banca, IDs e contratos relacionados.',
     'Moeda/valores são declarados pelo operador, sem aceitação ou custos verificados. Saldo usa unidade atual; drawdown exclui horário dos fluxos. Os dois arquivos têm snapshots separados.'),
    ('Liquidação e resumo preservam contrato, mando e significado da evidência',
     'Contrato importado inválido era liquidado; placar invertido ficava sob mando errado; ID estável exigia linha legada; NaN desativava teto; CLI afirmava CLV comprovado.',
     'Recusar contrato inconsistente, usar índices por ID/legado, normalizar placar ao mando gravado, validar teto finito e mostrar relatos manuais brutos sem selo econômico.',
     'before: contrato/placar/ID/teto/CLI reproduzidos; final: passam; teto negativo e liberação após erro já passavam antes. Fixture CPL recebeu line/period antes ausentes, sem mudar resultado esperado.',
     'Importações sem contrato completo falham sem reescrita; fatos históricos não corrigidos por inferência. Registro manual não autentica placar nem oferta. validated preservado apenas como flag legada.'),
]
for i, (claim, problem, action, proof, limit) in enumerate(items, 1):
    cid, pid = f'LGC-A{i:02}', f'LGC-P{i:02}'
    registry['claims'].append(dict(id=cid, claim=claim, origin='Revisão LGC, 10/09/2026', scope='bet_log.py',
        required='Reprodução sintética antes/depois e isolamento', found=problem + ' ' + action,
        evidence=proof, conclusion='refutada na base CLO; corrigida e validada no escopo delimitado', impact=limit, issue=pid))
    registry['issues'].append(dict(id=pid, claim=cid, problem=problem, type='integridade/contabilidade/concorrência',
        severity='alta', dependencies='bet_log.py; filesystem local; _canon permanece inalterado',
        action=action, closure_test=proof, status='validado', limitation=limit))
for issue in registry['issues']:
    if issue['id'] == 'CLO-P01':
        issue['limitation'] = 'Custos/aceite/unidade histórica sem certificação. Escritores cooperantes corrigidos em LGC-P01; arquivos operacionais não foram acessados.'

inventory = json.loads((prior / 'evidence/source-inventory.json').read_text())
by_path = {row['path']: row for row in inventory}
for name in ('brasileirao_predictor/bet_log.py', 'tests/test_completion_ledger.py', 'tests/test_bet_log.py',
             'tests/test_bet_id.py', 'tests/test_info_stake_cap.py', 'tests/test_closeout_integrity.py', 'tests/test_ledger_consistency.py'):
    path = repo / name
    by_path[name] = dict(path=name, **hash_file(path), lines=len(path.read_text(encoding='utf-8').splitlines()),
                        review='semantic_read_with_recorded_findings', evidence='LGC-P01..03 / testes sintéticos')
depth = dict(collections.Counter(row['review'] for row in by_path.values()))
dump(evidence / 'source-inventory.json', sorted(by_path.values(), key=lambda row: row['path']))
for issue in registry['issues']:
    if issue['id'] == 'CPL-P25':
        issue['action'] = f'Inventário cumulativo: {len(by_path)} arquivos; profundidades {depth}. LGC revisou integralmente o ledger e seus testes relacionados.'
dump(docs / 'REGISTROS.json', registry)
lines = ['# Registro central LGC\n', 'Consolida 26 itens CPL, 8 CLO e 3 LGC. Detalhes e referências cruzadas em [REGISTROS.json](REGISTROS.json). Registros históricos preservados nos diretórios de origem.\n',
         '| Alegação | Problema | Status | Ação |', '| --- | --- | --- | --- |']
for issue in registry['issues']:
    lines.append(f"| {issue['claim']} | {issue['id']}: {issue['problem'].replace('|', '/')} | {issue['status']} | {issue['action'].replace('|', '/')} |")
write(docs / 'REGISTROS.md', '\n'.join(lines) + '\n')
write(docs / 'RESULTADO.md', f'''# Consistência do livro-caixa — LGC-20260910

Base main/{sha}. Corrigidos os três grupos LGC do [registro central](REGISTROS.md), com 21 regressões reproduzidas antes e **95 testes aprovados, zero falhas/skips**, na execução final. **O mandato integral permanece aberto; lucro executável não foi demonstrado.**

A gravação cooperante tem exclusão entre processos e threads. O apêndice preserva o histórico e força flush/fsync. O saldo usa uma única leitura reconciliada de apostas; entradas bancárias inválidas são recusadas. Corrigidos mando do placar, dependência indevida de linha legada, contratos importados, teto não finito e rótulo de validação no CLI.

Técnica: pronta somente no escopo testado do livro manual em filesystem local Windows; sistema global não pronto. Ruff, formato e Pyright passaram nos três arquivos Python. Wheel/sdist construídos offline e instalação/CLI verificadas. Os 275 testes Python, 27 Redis e 127 .NET do checkpoint CLO são evidência anterior distinta; .NET/Redis não foram alterados nem repetidos nesta etapa.

Dados: parciais/insuficientes para execução comercial. Nenhum dado de jogo, preço real ou quota foi consumido nesta etapa. H14/H15/H9/A1, helper DC e bases operacionais não foram acessados/modificados. Inventário cumulativo: {len(by_path)} arquivos; profundidades {depth}. Inventário continua distinto de revisão semântica integral.

Economia: não mensurável como lucro executável. A decisão BE/CPL permanece congelada. O resultado hipotético de +4,6376u dependia de máximos anônimos e preenchimento de todas as pernas; o modelo de gols perdeu 99,60u. Correção de contabilidade não transforma esses resultados em apostas aceitas ou em lucro futuro.

As primeiras falhas estão preservadas: antes, 21 falhas/2 passagens; primeiro lote após correção, 94 passagens/1 falha por fixture de reordenação sem line/period. A fixture recebeu o contrato ou15/1,5/FT, mantendo a asserção sobre ID e exposição. O primeiro laboratório de processos recusou PID do launcher diferente do interpretador; o segundo usa o executável base, confirmou identidade do filho, exclusão entre processos e liberação automática da trava após seu encerramento. Nenhum processo operacional foi encerrado.

O isolamento final bloqueou três tentativas de subprocesso e uma de socket.bind antes de executarem; nenhuma foi liberada para fazer os testes passarem. O laboratório de processos é separado, restrito a filhos próprios, sem dados ou serviços operacionais. Os ramos POSIX das travas não foram executados neste Windows.

Limites: não há transação entre o livro bancário e o de apostas; leitores usam um snapshot de cada arquivo. Escritores externos que ignoram a trava, hardlinks distintos e filesystems remotos não foram homologados. Falha parcial de disco é recusada pela leitura estrita e exige reconciliação, não recuperação automática. Unidade histórica, câmbio, custos, cronologia dos fluxos no drawdown e autenticidade do relato continuam sem certificação. Importação sem contrato completo falha e não é reescrita.

Nenhuma API, automação, aposta ou experimento de desempenho novo foi executado. A próxima informação econômica decisiva continua sendo preço nominal simultâneo, estado/revisão e condições verificáveis de preenchimento/custos. A captura DC congelada de 11/09/2026 23:00 UTC trata somente sua dupla e não valida a carteira de três pernas. Os 14 itens econômicos e a descoberta que alterou a decisão permanecem em [CLO/RESULTADO](../closeout_2026-09-10/RESULTADO.md), sem revisão dos resultados BE.

Integração/restauração: C:/BRASILEIRAO/AUDITORIA/CONSISTENCIA_LEDGER_2026-09-10.json. [Continuação](PROXIMO_PROMPT.md), [mapa](MAPA_SISTEMA.md) e [reprodução](REPRODUZIR.md).
''')
write(docs / 'MAPA_SISTEMA.md', '''# Mapa vigente LGC

O [mapa CLO](../closeout_2026-09-10/MAPA_SISTEMA.md) mantém os demais subsistemas e limites. LGC substitui somente o estado de bet_log: CLI/manual → JSONL de apostas e banca → lista, liquidação e resumo brutos. Não é um executor financeiro.

| Componente | Dependência/consumidor | Decisão e prova |
| --- | --- | --- |
| _writer_lock / _single_writer | OS local; add/settle/bank_init/bank_flow | Corrigir: msvcrt Windows/fcntl POSIX, sidecar estável, erro imediato em conflito. Windows comprovado em threads/processos; POSIX não executado. |
| _append / _read_records | JSONL UTF-8; todos os consumidores manuais | Corrigir: LF se necessário sem alterar bytes antigos, flush/fsync, JSON estrito; corrupção recusa leitura. |
| bank_state | Snapshot bancário + um snapshot de apostas | Corrigir mistura de snapshots de apostas; escopo bruto e drawdown limitado explícitos. Sem transação entre os dois livros. |
| _settlement_index / settle_bet | MARKETS, _canon protegido e inalterado | Corrigir contratos/IDs/mando; preservar registros históricos e relatos como não autenticados. |
| main | Consumidor CLI | Retirar certificação indevida de CLV/mercado. validated mantido somente por compatibilidade. |

A contagem cumulativa em evidence/source-inventory.json preserva categorias e hashes anteriores, atualizando somente as fontes lidas/modificadas nesta etapa. A cobertura global permanece parcial. O arquivo protegido math_utils e os demais contratos H14/H15/H9/A1 não foram alterados. Não instalar nem executar operações protegidas para completar uma contagem.
''')
write(docs / 'MAPA_DADOS.md', '''# Dados e fontes LGC

Não houve nova aquisição nem leitura de dados operacionais. Os fixtures dos testes e do laboratório são inteiramente sintéticos. Datas de 2024 não são observações históricas reais. As evidências comerciais e bloqueios permanecem no [mapa CLO](../closeout_2026-09-10/MAPA_DADOS.md).

Registros bancários exigem JSON estrito, kind conhecido, valor/unidade positivos finitos, moeda declarada e timestamp com offset. Apostas importadas exigem mercado, seleção, período e linha coerentes. O código não preenche contrato ausente, não autentica o operador e não altera registros antigos. Publicação, recebimento de preço, aceite, custo pessoal e câmbio continuam desconhecidos para o ledger manual; não devem ser inferidos de logged_at/recorded_at.
''')
write(docs / 'REPRODUZIR.md', '''# Reprodução LGC

Ambiente RI: C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe, Python 3.13.12. Ferramentas, dependências e saídas em C:/BRASILEIRAO; Windows/PowerShell/Git e aplicativo continuam dependências externas inevitáveis.

Helpers e argumentos completos em C:/BRASILEIRAO/work/ledger-consistency-2026-09-10. run_isolated.py recebe um nome novo de saída e a lista explícita de seis arquivos em evidence/final/isolation.json. Nunca apontar testes para ledger operacional. process_lock_lab.py executa somente a trava, em filhos próprios com identidade conferida, e exige nova pasta de saída. A primeira versão falhou e está preservada em process_lock_lab-first.py.

check_changed.py verificou os três arquivos de código/teste; usa diff não staged, portanto não deve ser repetido cegamente após commit. build_package.py construiu offline e instalou em target próprio; logs e hashes estão em evidence/package-receipt-final.json. Relatórios finais foram escritos depois do build e são entregues separadamente. Backup verifica também igualdade de bytes do módulo no wheel e evidências do Git restaurado.

Não somar execuções sobrepostas como testes independentes: antes=23, primeiro depois=95, final=95. O laboratório de processos complementa, sem aumentar artificialmente esse contador.
''')
write(docs / 'PROXIMO_PROMPT.md', '''# Continuação após LGC

Leia o mandato original e consolidado. Trabalhe sozinho, com escritas em C:/BRASILEIRAO, sem tocar H14/H15/H9/A1, dependências protegidas, .env, dados ou Redis operacionais. Não prometer lucro e não declarar revisão integral concluída.

Confirme HEAD/main, trabalho concorrente e recibo AUDITORIA/CONSISTENCIA_LEDGER_2026-09-10.json. LGC corrige concorrência/consistência do livro manual; 95 testes aprovados, processos Windows verificados, qualidade e pacote aprovados. Não repetir suites já aprovadas sem nova alteração, falha ou dúvida concreta. Preservar as falhas anteriores e as travas laterais persistentes.

Continue pela cobertura semântica ainda parcial do registro CPL-P25, priorizando consumidores ativos e entradas capazes de invalidar decisões. Modelos residuais/artefatos e gates exploratórios têm validação ainda parcial; não reabrir dados vistos nem avaliar H14/H15/H9/A1. Módulos coletor/cache/modelo legados compartilhados precisam de sucessor separado se correção afetar coleta protegida.

Não abrir novo tuning para compensar o modelo BE reprovado. A oferta nominal simultânea e condições verificáveis de execução/custo seguem como dependência econômica. BE e orçamento CPL permanecem congelados. Não repetir HTTPs bloqueados sem mudança justificável. Não criar automação duplicada nem alterar captura DC; confira somente metadados/helpers/janela permitidos. Estado ativo da automação segue não verificável pelo retorno textual anterior.
''')
guides = ['README.md', 'HANDOFF.md', 'docs/ESTADO_ATUAL.md', 'docs/DATA_MAP.md',
          'docs/INDICE_DOCUMENTACAO.md', 'docs/continuation/RETOMADA.md']
previous = root / 'previous-guides'
previous.mkdir()
for name in guides:
    path = repo / name
    saved = previous / name
    saved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, saved)
    prefix = '**Atualização LGC-20260910:** integridade e concorrência do livro manual corrigidas; 95 testes aprovados e trava entre processos Windows verificada. [Resultado LGC](' + ('docs/continuation/' if '/' not in name else 'continuation/' if name.count('/') == 1 else '') + 'ledger_consistency_2026-09-10/RESULTADO.md). Revisão integral ainda aberta; lucro executável não demonstrado.\n\n'
    write(path, prefix + path.read_text(encoding='utf-8'))
path = base / 'LEIA_PRIMEIRO.md'
shutil.copyfile(path, previous / 'LEIA_PRIMEIRO.md')
write(path, '**Atualização LGC-20260910:** [resultado atual](brasileirao-predictor/docs/continuation/ledger_consistency_2026-09-10/RESULTADO.md). Livro manual com exclusão de escritores e saldo coerente; 95 testes aprovados. Mandato integral aberto e lucro executável não demonstrado.\n\n' + path.read_text(encoding='utf-8'))
target = base / 'INSTRUCOES/PROXIMO_PROMPT_APOS_CONSISTENCIA_LEDGER_2026-09-10.md'
assert not target.exists()
shutil.copyfile(docs / 'PROXIMO_PROMPT.md', target)
dump(evidence / 'manifest.json', {p.relative_to(docs).as_posix(): hash_file(p) for p in sorted(docs.rglob('*')) if p.is_file()})
print(json.dumps(dict(files=len(by_path), coverage=depth, tests=counts, records=len(registry['issues']))))
