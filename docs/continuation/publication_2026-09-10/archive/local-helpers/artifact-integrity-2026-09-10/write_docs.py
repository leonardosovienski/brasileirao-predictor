"""Dated artifact-integrity evidence and cumulative registry."""
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
prior = repo / 'docs/continuation/ledger_consistency_2026-09-10'
docs = repo / 'docs/continuation/artifact_integrity_2026-09-10'
start = '2220b42810aea6f656ed196507ff14a62349b83e'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() == start
docs.mkdir(exist_ok=False)
evidence = docs / 'evidence'
evidence.mkdir()

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def fingerprint(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

counts = {}
paths = []
for phase in ('before', 'after', 'final', 'consumer'):
    cases = list(ET.parse(root / phase / 'junit.xml').getroot().iter('testcase'))
    counts[phase] = dict(tests=len(cases), failures=sum(c.find('failure') is not None for c in cases),
                         errors=sum(c.find('error') is not None for c in cases), skips=sum(c.find('skipped') is not None for c in cases))
    paths += [f'{phase}/junit.xml', f'{phase}/isolation.json']
assert counts['before'] == dict(tests=24, failures=24, errors=0, skips=0)
assert counts['final'] == dict(tests=52, failures=0, errors=0, skips=0)
assert counts['consumer'] == dict(tests=2, failures=0, errors=0, skips=0)
assert all(row['exit_code'] == 0 for row in json.loads((root / 'quality-checks-final.json').read_text())['commands'])
package = json.loads((root / 'package-receipt-final.json').read_text())
assert len(package['commands']) == 7 and all(row['exit_code'] == row['expected'] for row in package['commands'])
paths += ['quality-checks-final.json', 'package-receipt-final.json']
paths += [p.relative_to(root).as_posix() for p in root.glob('*-final.log')]
paths += [p.relative_to(root).as_posix() for p in (root / 'quality-first').iterdir() if p.is_file()]
paths += [p.relative_to(root).as_posix() for p in (root / 'package-smoke-final').glob('*.log')]
for name in paths:
    target = evidence / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, target)
    assert fingerprint(target) == fingerprint(root / name)
shutil.copyfile(prior / 'evidence/.gitattributes', evidence / '.gitattributes')
shutil.copyfile(root / 'PLANO.md', docs / 'PLANO.md')
dump(evidence / 'validation-summary.json', dict(python=counts, unique_final_cases=54,
    final_executions=2, lint_format_typing='passed', synthetic_only=True,
    financial_execution=False, new_economic_experiment=False, network_acquisition=False,
    optimizer='BFGS unchanged objective/L2/sample; analytic derivatives checked by central finite differences',
    confidence_scope='conditional model Hessian approximation, not validated economic uncertainty'))
dc = base / 'work/data-completion-2026-09-09'
expected = {'followup_capture.py': '31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88',
            'audit_followup.py': 'ebce7ddeb384b347be4985b7a3812a1b83c7dfaceafdb3e2a6cb00f7e2d09a24'}
for name, sha in expected.items():
    assert fingerprint(dc / name)['sha256'] == sha
dump(evidence / 'followup-metadata.json', dict(checked_at=datetime.now(UTC).isoformat(), hashes=expected,
    attempt_exists=(dc / 'followup/attempt.json').exists(), receipt_exists=(dc / 'followup/receipt.json').exists(),
    decision_utc='2026-09-11T23:00:00Z', observation='metadata only; no execution, API, outcome or automation mutation',
    active_automation_status='unverified: earlier view exposed only UI card'))

registry = json.loads((prior / 'REGISTROS.json').read_text(encoding='utf-8'))
registry.update(round='ARI-20260910', dated_at=datetime.now(UTC).isoformat(), base=start,
                previous_registry='../ledger_consistency_2026-09-10/REGISTROS.json', mandate_complete=False)
claim = dict(id='ARI-A01', claim='Artefatos e ajuste residual publicam somente estados numéricos coerentes',
    origin='Pendência CLO reavaliada em ARI, 10/09/2026', scope='research/market_residual.py',
    required='Artefato finito/escala positiva/covariância válida; convergência; preservação de estado; derivadas verificadas',
    found='24 regressões reproduzidas. Validação no carregamento, inferência e exportação; cópia de arrays; fit transacional; target sem truncamento; expit estável e gradiente analítico da mesma função objetivo.',
    evidence='evidence/before, final e consumer; 54 casos finais únicos em duas execuções',
    conclusion='refutada na base LGC; corrigida e validada apenas com fixtures sintéticas',
    impact='Previne parâmetros inválidos e falsa precisão numérica; não autentica treino, oferta, custos ou rentabilidade',
    issue='ARI-P01')
registry['claims'].append(claim)
registry['issues'].append(dict(id='ARI-P01', claim='ARI-A01',
    problem='NaN/Inf/escalas e covariâncias inválidas eram aceitos; arrays emprestados mudavam modelo; sigmoid overflow; otimizador sem sucesso podia publicar estado; labels multinomiais truncados.',
    type='integridade numérica/artefato/modelagem', severity='alta', dependencies='market_residual.py; scipy/numpy; consumidores exploratórios',
    action=claim['found'], closure_test=claim['evidence'], status='validado',
    limitation='Não há artefato autenticado, avaliação econômica ou robustez estatística demonstrada. Covariância continua aproximação Hessiana condicional. Gates exploratórios e replay legado não homologados.'))
inventory = json.loads((prior / 'evidence/source-inventory.json').read_text())
indexed = {row['path']: row for row in inventory}
reviewed = ['brasileirao_predictor/research/market_residual.py', 'brasileirao_predictor/research/residual_walkforward.py',
            'brasileirao_predictor/research/residual_gate.py', 'brasileirao_predictor/research/calibration_gate.py',
            'tests/test_residual_artifact_integrity.py', 'tests/test_market_residual.py',
            'tests/test_residual_walkforward.py', 'tests/test_residual_gate.py', 'tests/test_calibration_gate.py']
for name in reviewed:
    path = repo / name
    indexed[name] = dict(path=name, **fingerprint(path), lines=len(path.read_text(encoding='utf-8').splitlines()),
                         review='semantic_read_with_recorded_findings', evidence='ARI-P01 / MAPA_SISTEMA; execução limitada à lista de testes')
depth = dict(collections.Counter(row['review'] for row in indexed.values()))
dump(evidence / 'source-inventory.json', sorted(indexed.values(), key=lambda row: row['path']))
for issue in registry['issues']:
    if issue['id'] == 'CPL-P25':
        issue['action'] = f'Inventário cumulativo de {len(indexed)} arquivos: {depth}. Cobertura semântica global continua parcial.'
dump(docs / 'REGISTROS.json', registry)
table = ['# Registro central ARI\n', '38 registros: 26 CPL, 8 CLO, 3 LGC e 1 ARI. [Detalhes e referências cruzadas](REGISTROS.json). Históricos anteriores preservados.\n',
         '| Alegação | Problema | Estado | Ação |', '| --- | --- | --- | --- |']
for issue in registry['issues']:
    table.append(f"| {issue['claim']} | {issue['id']}: {issue['problem'].replace('|', '/')} | {issue['status']} | {issue['action'].replace('|', '/')} |")
(docs / 'REGISTROS.md').write_text('\n'.join(table) + '\n', encoding='utf-8')
(docs / 'RESULTADO.md').write_text(f'''# Integridade dos artefatos residuais — ARI-20260910

Base main/{start}. Corrigida a pendência numérica do modelo residual, com **24 falhas reproduzidas antes e 54 testes aprovados depois**, em duas execuções finais sem falhas/skips. **A revisão integral permanece aberta e lucro executável não foi demonstrado.**

O carregamento recusa parâmetros não finitos, escalas não positivas, nomes inválidos e covariância assimétrica ou não semidefinida positiva. Arrays recebidos são copiados; inferência e exportação revalidam o estado. Treino malsucedido não substitui o modelo anterior. Labels multinomiais não são truncados. Sigmoid usa expit; BFGS mantém objetivo e regularização, com derivadas analíticas conferidas por diferenças centrais independentes nos dois modelos. A tolerância de covariância de 1e-12 vezes sua escala serve apenas a erro de arredondamento, sem ajuste por resultado econômico.

Técnica: pronta nos contratos numéricos testados; **sistema global não pronto**. Foram 52 casos finais do módulo/consumidor shadow e 2 do walk-forward sintético. Ruff, formato e Pyright passaram nos dois arquivos alterados. Primeiro check registrou uma linha longa e dois problemas de tipagem na fixture; corrigidos sem exclusões. Build offline, wheel/sdist e sete comandos de instalação/CLI passaram. Os testes LGC (95), CLO Python (275), Redis (27) e .NET (127) são lotes anteriores, com sobreposições; não somar como uma suíte nova.

Dados: **parciais/insuficientes para lucro executável**. Nenhum preço real, resultado de jogo, API ou quota foi consultado. Os testes usam amostras sintéticas fixas. A verificação DC foi apenas de hashes e existência de recibos: helpers inalterados, tentativa/recibo ausentes, corte mantido em 11/09/2026 23:00 UTC. Estado ativo da automação continua não verificável pelo retorno textual anterior. H14/H15/H9/A1 não foram avaliados nem modificados.

Economia: **não mensurável como execução real**. Nenhuma nova hipótese de performance, variante ajustada ou avaliação de estudo conhecido. O reader_contract_version residual-numerics/2 identifica o contrato de leitura/validação atual; não inventa a versão de treino de artefatos antigos. Capital permanece false, procedência não verificada e evidência econômica false. Covariância Hessiana é aproximação condicional ao modelo, não intervalo de lucro nem incerteza calibrada fora da amostra.

A descoberta operacional LGC permanece válida: concorrência e leituras incoerentes alteravam o livro manual. Seu commit 2220b42810aea6f656ed196507ff14a62349b83e foi restaurado e conferido, incluindo bytes dos arquivos de evidência. ARI corrige outra entrada capaz de invalidar a decisão, sem transformar engenharia em ganho econômico.

Inventário cumulativo: {len(indexed)} arquivos; profundidades {depth}. A leitura semântica global continua parcial. Gates e replay exploratórios ainda têm limitações registradas no [mapa](MAPA_SISTEMA.md); código compartilhado/coortes não foi alterado para completar cobertura. Docker/Compose local e feed comercial continuam não homologados.

A rodada econômica mantém os 14 itens do [resultado CLO](../closeout_2026-09-10/RESULTADO.md): investigar a possibilidade de obter oferta nominal simultânea e preencher as pernas nas condições de custo. O envelope BE de +4,6376u dependia de máximos anônimos e preenchimento hipotético; o modelo de gols perdeu 99,60u e segue sem prioridade. O que decide avanço é preço identificado, estados/revisões e preenchimento/custos verificáveis. A captura DC congelada trata somente sua dupla, sem validar a carteira de três pernas.

[Registros centrais](REGISTROS.md), [reprodução](REPRODUZIR.md) e [continuação](PROXIMO_PROMPT.md). Integração, SHA, pacote e restauração em C:/BRASILEIRAO/AUDITORIA/INTEGRIDADE_ARTEFATOS_2026-09-10.json. Nenhum push, implantação, aposta ou habilitação financeira.
''', encoding='utf-8')
(docs / 'MAPA_SISTEMA.md').write_text('''# Mapa vigente ARI

O [mapa LGC](../ledger_consistency_2026-09-10/MAPA_SISTEMA.md) e seu mapa CLO referenciado continuam válidos para os demais subsistemas. ARI atualiza o modelo residual experimental, sem implantação.

| Componente | Estado e decisão | Evidência/limite |
| --- | --- | --- |
| MarketResidualModel | Corrigir carregamento, cópia, estado, convergência, intervalo e exportação | 24 regressões antes/depois; aproximação Hessiana não autentica treino nem calibração econômica. |
| MultinomialMarketResidualModel | Corrigir truncamento de labels, pré-processamento transacional, convergência e estado | Classes 0/1/2 mantidas, objetivo e L2 inalterados, gradiente conferido. |
| economic_decision | Consumidor do contrato ResidualPrediction preservado | Testes sintéticos correlatos passam; sempre shadow/capital false. |
| residual_walkforward | Consumidor exploratório, preservado | Dois testes sintéticos passam. Não é replay financeiro: roi é média de retornos por seleção em unidade fixa; stake da decisão não é aplicada como carteira com banca. Dados/IDs/status/revisões precisam de protocolo próprio. |
| residual_gate | Exploração preservada, fora do caminho econômico ativo | Leitura semântica: input admite bool/não finitos; pnl médio chamado ROI depende de stake fixa; DSR fornecido pelo chamador e dependência PSR não resolvida. Não autentica promoção; não executado nesta etapa. |
| calibration_gate | Gate A10 histórico, preservado | Leitura semântica: coerção float/não finitos podem alterar juízo; relatório é declaração, não prova de procedência. Estudo congelado não foi recalculado; não usar como homologação econômica. |

Os scripts históricos que usam esses componentes não foram executados sobre dados reais. Alterar avaliação congelada não é necessário para testar o consumidor puro; erros remanescentes não foram ocultados nem classificados como validados. O registro CPL-P25 mantém a continuação da cobertura global.
''', encoding='utf-8')
(docs / 'MAPA_DADOS.md').write_text('''# Dados e fontes ARI

Sem nova aquisição. Evidências históricas, recibos públicos e bloqueios continuam no [mapa CLO](../closeout_2026-09-10/MAPA_DADOS.md). Fixtures desta etapa são artificiais; nenhum placar/cotação foi buscado. Há datas de 2024 em teste, sem alegação de observação histórica real.

Artefato numérico válido continua sem procedência de treino autenticada. Hash prova igualdade de bytes e não legitimidade, disponibilidade comercial ou aceitação. reader_contract_version não é versão de treino. Nomes/escala/covariância coerentes não certificam features PIT. Evidência DC em evidence/followup-metadata.json contém somente hashes, clocks e existência de arquivos; não conteúdo de coortes nem credenciais.
''', encoding='utf-8')
(docs / 'REPRODUZIR.md').write_text('''# Reprodução ARI

Ambiente RI Python 3.13.12 em C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe. Helpers em C:/BRASILEIRAO/work/artifact-integrity-2026-09-10. Windows, Git, PowerShell e aplicativo são dependências externas inevitáveis.

run_isolated.py exige um diretório novo e lista explícita: test_residual_artifact_integrity.py, test_market_residual.py e test_closeout_research_inputs.py (52 casos); test_residual_walkforward.py foi executado separadamente (2 casos). Não executar sobre dados reais nem repetir o gate A10 ou coortes para esta reprodução. Isolamento final recusou socket.bind antes de acesso; nenhuma liberação de rede foi necessária.

before contém 24 falhas; after contém 50 passagens; final contém 52 passagens, incluindo duas verificações adicionais de gradiente; consumer contém 2 passagens. Contagem final única=54, não soma de todos os lotes. quality-first preserva os checks iniciais; quality-checks-final tem os comandos aprovados. check_changed.py usa diff não staged, portanto adaptar a lista se o código já estiver commitado.

build_package.py cria wheel/sdist offline e instala em target próprio; hashes/logs em evidence/package-receipt-final.json. Docs finais foram escritos depois do pacote e são entregues separadamente. Backup verifica bytes do módulo no wheel, ZIP e evidências no Git restaurado. Sem restore de DB/Redis/coortes operacionais.
''', encoding='utf-8')
(docs / 'PROXIMO_PROMPT.md').write_text('''# Continuação após ARI

Leia integralmente os dois mandatos em C:/BRASILEIRAO/INSTRUCOES. Trabalhe sozinho e escreva somente em C:/BRASILEIRAO. Preserve H14/H15/H9/A1, dependências, agendas, helpers congelados e dados operacionais; não exponha credenciais.

Confirme main/HEAD, concorrência, diff e AUDITORIA/INTEGRIDADE_ARTEFATOS_2026-09-10.json. ARI corrige fronteiras numéricas de modelos residuais, com 54 testes finais únicos, qualidade e pacote aprovados. LGC corrige livro manual (95 casos), CLO tem 275 Python/27 Redis/127 .NET. Não somar lotes sobrepostos nem repetir sem mudança ou dúvida concreta. Resultados econômicos continuam congelados e lucro não foi demonstrado.

Cobertura semântica global ainda parcial (CPL-P25). Continue revisão por consumidor e impacto; não reabra estudos conhecidos para criar holdout novo. Gates exploratórios e replay legado continuam fora do caminho econômico ativo e não homologados. Coletores/cache/modelos compartilhados protegidos não podem ser alterados diretamente; sucessores isolados somente quando necessários ao caminho justificado.

BE mantém prioridade na oferta nominal simultânea e condições verificáveis de execução/custos. Não retunar o modelo de gols reprovado. Captura DC fixa de 11/09/2026 23:00 UTC permanece com os mesmos helpers, fixture, casas, janela, reserva20 e quota; não antecipar, duplicar automação nem reconstruir chegada tardia. A configuração ativa do aplicativo não foi comprovada pela ferramenta textual. Não prometer lucro nem declarar o mandato integral concluído.
''', encoding='utf-8')
guides = ['README.md', 'HANDOFF.md', 'docs/ESTADO_ATUAL.md', 'docs/DATA_MAP.md', 'docs/INDICE_DOCUMENTACAO.md', 'docs/continuation/RETOMADA.md']
archive = root / 'previous-guides'
archive.mkdir()
for name in guides:
    path = repo / name
    target = archive / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    relative = ('docs/continuation/' if '/' not in name else 'continuation/' if name.count('/') == 1 else '') + 'artifact_integrity_2026-09-10/RESULTADO.md'
    path.write_text(f'**Atualização ARI-20260910:** artefatos e otimização residual corrigidos; 54 testes aprovados, com dados sintéticos. [Resultado atual]({relative}). Revisão integral aberta; lucro executável não comprovado.\n\n' + path.read_text(encoding='utf-8'), encoding='utf-8')
guide = base / 'LEIA_PRIMEIRO.md'
shutil.copyfile(guide, archive / 'LEIA_PRIMEIRO.md')
guide.write_text('**Atualização ARI-20260910:** [resultado atual](brasileirao-predictor/docs/continuation/artifact_integrity_2026-09-10/RESULTADO.md). Artefatos residuais corrigidos, 54 testes aprovados. Mandato integral aberto e lucro executável não demonstrado.\n\n' + guide.read_text(encoding='utf-8'), encoding='utf-8')
target = base / 'INSTRUCOES/PROXIMO_PROMPT_APOS_INTEGRIDADE_ARTEFATOS_2026-09-10.md'
assert not target.exists()
shutil.copyfile(docs / 'PROXIMO_PROMPT.md', target)
dump(evidence / 'manifest.json', {p.relative_to(docs).as_posix(): fingerprint(p) for p in sorted(docs.rglob('*')) if p.is_file()})
print(json.dumps(dict(coverage=depth, files=len(indexed), records=len(registry['issues']), counts=counts)))
