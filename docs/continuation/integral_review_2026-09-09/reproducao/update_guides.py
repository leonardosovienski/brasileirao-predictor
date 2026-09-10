"""Update only current entry guides; keep prior versions in a dated RI snapshot."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = Path('C:/BRASILEIRAO')
REPO = BASE / 'brasileirao-predictor'
RI = REPO / 'docs/continuation/integral_review_2026-09-09'
old = ROOT / 'previous-guides'
old.mkdir(exist_ok=False)
paths = ['README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/continuation/RETOMADA.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md']
for rel in paths:
    dest = old / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((REPO / rel).read_bytes())
(old / 'LEIA_PRIMEIRO.md').write_bytes((BASE / 'LEIA_PRIMEIRO.md').read_bytes())

def put(path, text):
    path.write_text(text.strip() + '\n', encoding='utf-8')

put(REPO / 'README.md', '''
# brasileirao-predictor

Pesquisa quantitativa e software de previsão para o Brasileirão Série A.
**Raiz local: C:/BRASILEIRAO. Projeto globalmente não pronto; lucro executável não demonstrado; capital bloqueado.**

## Comece aqui

A [revisão RI-20260909](docs/continuation/integral_review_2026-09-09/RESULTADO.md) conferiu o existente, corrigiu defeitos e validou o escopo permitido. Seus mapas distinguem software testado, dados admissíveis e bloqueios. H14/H15/H9/A1 permanecem protegidos; conclusão da revisão não significa realização do objetivo econômico.

1. [Estado atual](docs/ESTADO_ATUAL.md) e [retomada](docs/continuation/RETOMADA.md).
2. [Matriz de alegações](docs/continuation/integral_review_2026-09-09/ALEGACOES.md) e [problemas/correções](docs/continuation/integral_review_2026-09-09/PROBLEMAS.md).
3. [Mapa do sistema](docs/continuation/integral_review_2026-09-09/MAPA_SISTEMA.md), [dados](docs/DATA_MAP.md) e [índice documental](docs/INDICE_DOCUMENTACAO.md).
4. [Próximo prompt](docs/continuation/integral_review_2026-09-09/PROXIMO_PROMPT.md), [mandato](docs/continuation/MANDATO_LUCRO_2026-09-09.md) e [histórico](HANDOFF.md).

## Resultado e evidência

A RI corrigiu admissão de identidade/estado/clocks, JSON ambíguo, concorrência de publicação, agrupamento temporal e backtest de eventos. O simulador de Copa recusa liga antes de abrir banco; importar helpers de backtest não cria log operacional. O auditor independente da captura futura recebeu a versão testada, mantendo coletor, fixture, horário e agenda.

Foram reconferidos 177 históricos íntegros, 380 jogos de 2025 e três capturas de um evento. Zero execuções admitidas. A perda condicional já conhecida de 9,24u foi reproduzida, sem novo holdout ou otimização de filtros. Hash/recibo atual não comprova oferta executável no passado. Referência independente sem margem não é probabilidade verdadeira.

Nos lotes isolados, 1.291 casos únicos têm último resultado aprovado e um foi pulado; não se trata da suíte integral. O pacote Python foi construído e sua ajuda da CLI funcionou; .NET 10 compilou, com 69 testes aprovados e 41 pulados. Ruff no escopo CI e tipagem padrão/explicitamente ampliada passaram. [Evidências e limites](docs/continuation/integral_review_2026-09-09/REPRODUZIR.md).

## Instalação e operação são estados diferentes

| Componente | Estado conferido na RI |
| --- | --- |
| Repo e histórico | C:/BRASILEIRAO/brasileirao-predictor, main; base inicial ac22c56, integração no recibo de auditoria |
| Ambiente de pesquisa completo | C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv; Python 3.13.12, Core 3.2.0/Ops 4.1.0 e extras fixados |
| SDK .NET portátil | C:/BRASILEIRAO/work/revisao-integral-2026-09-09/dotnet-sdk; 10.0.401, build em cópia isolada |
| Ambiente mínimo da captura | C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv; preservado |
| Dados e recibos DC | C:/BRASILEIRAO/work/data-completion-2026-09-09; sem reescrever raws |
| Entrega RI | C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_RI_20260909 |
| Redis/Compose/serving operacional | Não iniciados ou integralmente validados; Docker não localizado no host |
| Agenda independente | Existente na tarefa anterior; estado atual não legível na consulta RI. Não duplicar; protocolo DC preservado |

## Desenvolvimento e continuidade

Use a [reprodução isolada RI](docs/continuation/integral_review_2026-09-09/REPRODUZIR.md). O serving legado aproxima odds/cache e não é caminho admissível para decisão financeira. O simulador implementa Copa, não temporada de liga. Mocks de WebSocket/Redis, testes e melhora preditiva não demonstram execução comercial.

A captura fixa de 11/09/2026, antes da decisão às 23:00 UTC, é descrita em [CONTINUIDADE DC](docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md), com atualização RI no estado/retomada. Não repetir lotes, mudar janela, buscar resultado do fixture ou acionar coortes para preencher a revisão.

Nenhuma aposta, login/cadastro de apostas, compra, movimentação de capital, avaliação protegida ou alteração de dependência da coleta está autorizada. Dados e configurações privados permanecem fora do Git e dos processos de pesquisa. [Migração](docs/MIGRACAO_WINDOWS.md) e [documentos históricos](docs/history/antes_consolidacao_2026-09-09/README.md) mantêm seu escopo datado. [Publicação anterior](docs/continuation/publication_2026-09-09/README.md) não é CI ou recibo das alterações RI.
''')

put(REPO / 'docs/ESTADO_ATUAL.md', '''
# Estado atual — RI-20260909

Revisão executada em 09/09 à noite de São Paulo (recibos UTC em 10/09). Raiz C:/BRASILEIRAO, trabalho solo. **Projeto globalmente não pronto; dados insuficientes para execução em T−60; lucro líquido executável não mensurável.** [Resultado completo](continuation/integral_review_2026-09-09/RESULTADO.md), [registros centrais](continuation/integral_review_2026-09-09/REGISTROS.json) e [próximo prompt](continuation/integral_review_2026-09-09/PROXIMO_PROMPT.md).

## Base, ambiente e verificação

Checkout main, base inicial e remoto conferido ac22c56c3318623e07a722f34d44dc6cd877ea37, sem mudanças locais iniciais ou AGENTS.md aplicável. Commit final, diff e backup: C:/BRASILEIRAO/AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json. Históricos e branches preservados, sem reset/force-push.

Foi instalado novo ambiente RI em work/revisao-integral-2026-09-09/venv: Python 3.13.12, pytest 9.1.1, Ruff 0.16.6, Pyright 1.1.411, Core 3.2.0, Ops 4.1.0 e extras do uv.lock. O ambiente mínimo PF, usado pela captura, ficou inalterado. SDK.NET10.0.401 portátil e caches em RI; build em cópia pública isolada do código. Sistema Windows, Git, aplicativo Codex e serviços externos não pertencem à garantia da pasta.

1.291 casos únicos com último resultado aprovado e um skip nos lotes delimitados; quatro ensaios da barreira de isolamento aprovados. Não é suíte única integral. .NET: restore/build Release --warnaserror e 69 testes aprovados, 41 de integração pulados. Python: sdist/wheel e ajuda da CLI a partir do wheel passaram. Ruff/format no escopo CI passaram (390 arquivos); tipagem padrão exclui research, complementada por quatro arquivos explícitos. O lint de todo o repo achou 805 questões em cópias históricas fora da CI, preservadas. [Reprodução e logs](continuation/integral_review_2026-09-09/REPRODUZIR.md).

CI success confirmado apenas na base ac22c56, run34419406215. Não atribuir esse resultado ao código RI. Docker ausente do PATH e local padrão; Redis/Compose real e aplicação operacional não foram iniciados. O worker usa contrato genérico de feed e não comprova oferta/execução comercial.

## Dados e conclusões

177/177 históricos DC conferidos por SHA256/bytes, 623.271.596 bytes. Os recibos são posteriores às decisões históricas; idade da última mudança não é idade do recebimento. CSV 2025: 380 partidas, 20 clubes, 38 jogos por clube, sem duplicação de pares dirigidos. Três capturas representam um evento, zero pares API admitidos e zero execuções.

A conta DC congelada foi reproduzida sem novo candidato: 32 apostas condicionais, 348 abstenções, stakes32u, custo0,64u, retorno incluindo principal23,40u, banca100→90,76u, perda9,24u. Fonte/clock e referência comprometidos impedem interpretar isso como ROI executável. Nenhum label de 2026 ou de coorte protegida foi lido para avaliação.

Quatro contratos públicos recuperados e duas tentativas Football-Data HTTP503; sem consulta autenticada, consumo de reserva, conta ou compra. Condições pessoais de capacidade, moeda, custo, aceite e validação futura seguem ausentes. [Mapa detalhado](continuation/integral_review_2026-09-09/MAPA_DADOS.md).

## Correções e caminho ativo

Admissão independente passa a rejeitar participantes/competição trocados, estados contraditórios, clocks ausentes/futuros, JSON duplicado/não finito; publicação final não substitui auditoria concorrente. TemporalPolicy v2 conserva o dia UTC com kickoff parcial; event-backtest/v2 separa dias, deduplica alvos e abstém por mercados/probabilidades/odds não suportados. Import não grava log operacional. Simulador recusa liga antes de abrir DB.

Serving legado (predict/display) não estabelece identidade e clocks de preços suficientes; permanece fora do caminho de decisão econômica. Config/modelos e dependências capazes de mudar coleta protegida não foram alterados. Não ligar xG/ajustar filtros para encobrir falta de preços/custos. [Problemas e critérios de fechamento](continuation/integral_review_2026-09-09/PROBLEMAS.md).

## Agenda independente

ID completar-dados-do-brasileir-o, tarefa anterior01a08756-2962-7c43-9773-c790cc81329d. A consulta atual via view apenas apresentou cartão, sem estado legível ao modelo; o TOML de AUDITORIA é histórico. Não afirmar agenda ativa a partir dessa cópia e não duplicar. Na conferência RI não havia tentativa followup ou processo de captura concorrente.

Coletor followup_capture.py preservado (SHA 31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88). Auditor audit_followup.py corrigido ativado (SHA ebce7ddeb384b347be4985b7a3812a1b83c7dfaceafdb3e2a6cb00f7e2d09a24), com versão anterior guardada. Fixture/casas/decisão/janela/reserva20/quota/agenda não mudaram. [Ativação](continuation/integral_review_2026-09-09/evidence/activation.json).

Decisão11/09/2026 23:00UTC (20:00 São Paulo), kickoff12/09 00:00UTC, fixture id1000032566887012, Pinnacle/bet365.bet.br. Seguir [protocolo DC](continuation/data_completion_2026-09-09/CONTINUIDADE.md) e o próximo prompt RI; sem coleta antecipada, retry não autorizado, mudança retrospectiva ou consulta de desfecho.

## Preservação e limites

H14/H15/H9/A1 integralmente preservados: sem resultados intermediários, métricas, avaliadores, claims, agendas, DB/Redis operacionais ou mudanças de dependências da coleta. A cobertura dessas áreas limita-se a metadados/contratos permitidos. A revisão não as homologou.

Migração anterior: recibo de 12.423 entradas mais manifesto, 9.477.623.208 bytes e cinco snapshots, sem nova abertura do conteúdo protegido. O novo backup verifica recuperação Git em repositório bare, sem restaurar operação. Não garante arquivos nunca enviados, ferramentas de sistema ou alterações posteriores no computador antigo. [Mapa geral](DATA_MAP.md), [mandato](continuation/MANDATO_LUCRO_2026-09-09.md) e [histórico](../HANDOFF.md).
''')

put(REPO / 'docs/continuation/RETOMADA.md', '''
# Retomada após RI-20260909

Leia o [próximo prompt](integral_review_2026-09-09/PROXIMO_PROMPT.md), [estado atual](../ESTADO_ATUAL.md), [resultado RI](integral_review_2026-09-09/RESULTADO.md), [registros](integral_review_2026-09-09/REGISTROS.json) e mandato original em C:/BRASILEIRAO/INSTRUCOES/MANDATO_RECEBIDO_2026-09-09.txt. Trabalhe sozinho. O prompt final original foi executado no escopo permitido; não apagar correções ou recomeçar estudos já vistos.

## Checkpoint

Base inicial main/ac22c56; integração e recuperação Git no recibo C:/BRASILEIRAO/AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json. Novo ambiente completo de pesquisa e SDK10 em C:/BRASILEIRAO/work/revisao-integral-2026-09-09. 1.291 casos únicos com último resultado aprovado/um skip em lotes delimitados; .NET69 aprovados/41 pulados; build e pacote Python, Ruff e tipagem passaram. Sem homologação integral ou operação real.

Admissão, JSON, concorrência, temporalidade e backtest de eventos corrigidos. Todos177 históricos íntegros;380jogos2025;3capturas/1evento;zero execuções admitidas. Conta congelada−9,24u reproduzida como cenário, sem nova validação. Preços temporais/capacidade/custos continuam o requisito decisivo; novo modelo foi despriorizado.

## Próxima ação justificada

Conferir estado atual da automação existente completar-dados-do-brasileir-o, pertencente à tarefa anterior01a08756-2962-7c43-9773-c790cc81329d. A RI recebeu apenas cartão sem estado legível, não confirmou agenda ativa e não criou outra. Cópia histórica em AUDITORIA não prova execução. Preserve o [protocolo DC](data_completion_2026-09-09/CONTINUIDADE.md).

Captura fixa: fixture id1000032566887012,Pinnacle/bet365.bet.br,decisão11/09/2026 23:00UTC,kickoff12/09 00:00UTC. Janela de início22:55–22:59:15UTC,alvo22:58:30UTC,conta gratuita,reserva20,máximo1consulta de odds. Antes da janela não consumir API. Chegada tardia não autoriza outro corte ou reconstrução. Não consultar desfecho do fixture.

Helpers em work/data-completion-2026-09-09. Coletor inalterado; auditor RI ativado com recibo e backup,hashes no estado atual. Depois de captura, auditar em processo separado sem credenciais; uma observação válida ainda não demonstra aceite,capacidade,custo ou lucro. Não repetir ensaios sem nova alteração/falha. Após auditoria ou12/09,reavaliar e pausar o acompanhamento existente se não houver ação útil autorizada.

## Outros requisitos abertos

Os [problemas centrais](integral_review_2026-09-09/PROBLEMAS.md) documentam: feed/Redis/Compose real em ambiente descartável; consumidor de odds com identidade/clocks estritos; capacidade/custos verificáveis; limites da recuperação e da operação protegida. Não apontar testes a DB/Redis existentes ou modificar dependências da coleta. Não preencher esses campos com estimativas tratadas como observação.

Entregas RI em C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_RI_20260909; código/recibos compactos em integral_review_2026-09-09; rawsDC intactos. [Reprodução](integral_review_2026-09-09/REPRODUZIR.md). Preserve históricos PF/DC/ER,negativos,protocolos e todas as tentativas. Nenhuma ação financeira, compra, conta de apostas ou avaliação H14/H15/H9/A1 autorizada.
''')

data_map = (old / 'docs/DATA_MAP.md').read_text(encoding='utf-8')
intro = '''
## Revisão RI-20260909: situação mais recente

A [revisão de campos/fontes](continuation/integral_review_2026-09-09/MAPA_DADOS.md) reconferiu os177 históricos,CSV2025 e piloto,sem reabrir bancos protegidos. Estado: arquivos íntegros,execução histórica inadmissível/insuficiente;lucro executável não mensurável. [Resultado](continuation/integral_review_2026-09-09/RESULTADO.md).

- `C:/BRASILEIRAO/work/revisao-integral-2026-09-09`: venv completo,SDK10 portátil,inventário,contratos públicos,ensaios,logs,conta independente e backups dos guias/helpers anteriores.
- `C:/BRASILEIRAO/brasileirao-predictor/docs/continuation/integral_review_2026-09-09`: registros centrais,mapas,protocolo,relatório,próximo prompt e evidências sanitizadas.
- `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_RI_20260909`: cópia conferida da entrega RI.
- `C:/BRASILEIRAO/AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json`: integração,hashes,diff,cópias e recuperação Git. Não é recuperação operacional dos dados protegidos.

Nenhum rawDC foi reescrito; apenas o auditor futuro independente foi atualizado com backup/hash. O estado atual da agenda não pôde ser lido pela ferramenta; TOML antigo é documental. O restante deste mapa descreve locais e recibos anteriores,com seu escopo/datamento preservado.

'''
data_map = data_map.replace('## Armazenamento atual', intro + '## Armazenamento atual', 1)
put(REPO / 'docs/DATA_MAP.md', data_map)

handoff = (old / 'HANDOFF.md').read_text(encoding='utf-8')
checkpoint = '''
## 09/09/2026 — revisão RI concluída no escopo permitido

Leia primeiro [resultado RI](docs/continuation/integral_review_2026-09-09/RESULTADO.md), [registros centrais](docs/continuation/integral_review_2026-09-09/REGISTROS.json) e [próximo prompt](docs/continuation/integral_review_2026-09-09/PROXIMO_PROMPT.md). Base ac22c56. A revisão agora foi executada; entradas mais antigas abaixo descrevem seu próprio estágio e não invalidam este checkpoint.

Corrigidos admissão de identidade/estado/JSON,publicação concorrente,agrupamento temporal,treino/abstenção no backtest de eventos,import que escrevia log e recusa tardia do simulador de Copa. Novo venv completo e SDK.NET10;1.291 casos únicos aprovados/um skip em lotes delimitados;.NET69/41skip;build/pacote/lint/tipagem documentados.177 históricos íntegros,380 jogos2025,3capturas/1evento;conta condicional−9,24u reproduzida. Zero execução admitida; projeto não pronto e lucro executável não mensurável.

Auditor independente corrigido ativado;coletor,fixture,casas,decisão,janelas,quota e agenda preservados. Agenda pertence à tarefa anterior;estado atual não confirmado pela resposta legível da ferramenta,não duplicar. H14/H15/H9/A1 e DB/Redis operacionais intocados. Integração/cópias/backup em C:/BRASILEIRAO/AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json. Não reabrir históricos como holdout nem executar avaliações protegidas.

'''
first, rest = handoff.split('\n', 1)
put(REPO / 'HANDOFF.md', first + '\n\n' + checkpoint + rest)

put(BASE / 'LEIA_PRIMEIRO.md', '''
# BRASILEIRAO — leia primeiro

**Revisão RI-20260909 executada no escopo permitido. Projeto globalmente não pronto; lucro executável não demonstrado; capital bloqueado.** Toda entrega desta revisão permanece em C:/BRASILEIRAO. Recibos UTC de10/09 correspondem à noite de09/09 de São Paulo.

- [Estado atual](brasileirao-predictor/docs/ESTADO_ATUAL.md).
- [Resultado e conclusões RI](brasileirao-predictor/docs/continuation/integral_review_2026-09-09/RESULTADO.md).
- [Alegações](brasileirao-predictor/docs/continuation/integral_review_2026-09-09/ALEGACOES.md), [problemas](brasileirao-predictor/docs/continuation/integral_review_2026-09-09/PROBLEMAS.md) e [mapa do sistema](brasileirao-predictor/docs/continuation/integral_review_2026-09-09/MAPA_SISTEMA.md).
- [Retomada](brasileirao-predictor/docs/continuation/RETOMADA.md) e [próximo prompt](INSTRUCOES/PROXIMO_PROMPT_APOS_REVISAO_2026-09-09.md).
- [Mandato original](INSTRUCOES/MANDATO_RECEBIDO_2026-09-09.txt), [prompt consolidado executado](INSTRUCOES/PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md), [mapa de dados](brasileirao-predictor/docs/DATA_MAP.md) e [índice](brasileirao-predictor/docs/INDICE_DOCUMENTACAO.md).

O repo está em brasileirao-predictor. A revisão completa e suas evidências estão em ENTREGAS/BRASILEIRAO_RI_20260909 e work/revisao-integral-2026-09-09. O ambiente mínimo da captura foi preservado; o novo ambiente de pesquisa tem dependências completas e SDK.NET10 portátil. Build/testes isolados não significam Redis/Compose ou aplicação operacional ativos.

Os177 históricos eCSV de380jogos2025 foram reconferidos;3capturas são1evento. A conta conhecida perdeu9,24u apenas em cenário condicional. Corrigiram-se admissão,temporalidade,concorrência e backtest. O auditor independente foi atualizado por hash; captura e agenda congeladas não mudaram. A agenda está vinculada à tarefa anterior,sem confirmação de estado legível na ferramenta RI; não duplicar.

MIGRACAO_DADOS eDADOS_PRESERVADOS mantêm os pacotes/snapshots recebidos. O recibo anterior cobre12.423arquivos+manifesto,9.477.623.208bytes; não é imagem integral do computador antigo nem prova de arquivos nunca enviados. BACKUPS contém bundles Git;recuperação/cópias da RI constam de AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json. H14/H15/H9/A1,claims,observadores,avaliadores e dependências de coleta permanecem protegidos. Nenhum banco/Redis operacional ou ação financeira foi iniciado por esta revisão.
''')
(BASE / 'INSTRUCOES/PROXIMO_PROMPT_APOS_REVISAO_2026-09-09.md').write_bytes((RI / 'PROXIMO_PROMPT.md').read_bytes())

manifest_path = REPO / 'docs/continuation/data_completion_2026-09-09/reproducao/manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
activation = json.loads((ROOT / 'activation-receipt.json').read_text(encoding='utf-8-sig'))
manifest.update(revision_updated_at=activation['at_utc'],revision_round='RI-20260909; only audit_followup.py changed; collector protocol preserved',
                previous_version_commit='ac22c56c3318623e07a722f34d44dc6cd877ea37',
                previous_manifest_sha256=hashlib.sha256((ROOT / 'previous-active/manifest.json').read_bytes()).hexdigest())
manifest['files']['audit_followup.py'] = activation['active_sha256']
put(manifest_path,json.dumps(manifest,ensure_ascii=False,indent=2))

# Index all Markdown paths, using metadata only for protected/historical files.
docs = sorted(p for p in REPO.rglob('*.md') if '.git' not in p.parts and '.venv' not in p.parts)
lines = ['# Índice da documentação — RI-20260909','',
         'Estado vigente: [ESTADO_ATUAL.md](ESTADO_ATUAL.md). [Resultado RI](continuation/integral_review_2026-09-09/RESULTADO.md), [retomada](continuation/RETOMADA.md) e [próximo prompt](continuation/integral_review_2026-09-09/PROXIMO_PROMPT.md).', '',
         'Inventário por caminho, sem reabrir conteúdo protegido. Documentos históricos conservam contexto, resultados e contratos. A revisão RI foi executada no escopo permitido, sem homologar coortes ou aplicação completa. Os inventários externos da migração permanecem em C:/BRASILEIRAO/AUDITORIA.', '',
         f'## Inventário completo: {len(docs)} documentos', '', '| Documento | Categoria |', '| --- | --- |']
import os
for path in docs:
    rel = path.relative_to(REPO).as_posix()
    link = Path(os.path.relpath(path,REPO/'docs')).as_posix()
    category = 'Revisão RI — estado e evidência datados' if '/integral_review_2026-09-09/' in rel else 'Guia atual' if rel in paths else 'Histórico/contrato/documentação — preservar escopo original'
    lines.append(f'| [{rel}]({link}) | {category} |')
put(REPO/'docs/INDICE_DOCUMENTACAO.md','\n'.join(lines))
print(json.dumps({'updated':paths+['C:/BRASILEIRAO/LEIA_PRIMEIRO.md'],'markdown_count':len(docs),'snapshot':str(old)},ensure_ascii=False))
