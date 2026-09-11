"""Publish the current implementation report from completed local evidence."""

import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/BRASILEIRAO/brasileirao-predictor')
DOC = REPO / 'docs/continuation/implementation_2026-09-10'
EVIDENCE = DOC / 'evidence'
EVIDENCE.mkdir(parents=True, exist_ok=True)


def write(path, text):
    path.write_text(text.strip() + '\n', encoding='utf-8', newline='\n')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


runtime = read(ROOT/'runtime-04-final/receipt.json')
assert runtime['server_stopped'] and all(c['exit_code'] == 0 for c in runtime['commands'])
unit = ET.parse(ROOT/'unit-final/junit.xml').getroot().find('testsuite')
assert unit.attrib['failures'] == '0' and unit.attrib['errors'] == '0'
integration = ET.parse(ROOT/'runtime-04-final/python-junit.xml').getroot().find('testsuite')
assert integration.attrib['failures'] == '0'
trx = ET.parse(next((ROOT/'runtime-04-final/dotnet-results').glob('*.trx')))
ns = {'t':'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
counts = trx.find('.//t:Counters',ns).attrib
assert counts['passed'] == counts['total'] == '110'
coverage = ET.parse(next((ROOT/'runtime-04-final/dotnet-results').rglob('coverage.cobertura.xml'))).getroot().attrib
decision = read(ROOT/'capture-experiment-02/decision.json')
assert decision['reason'] == 'LATEST_API_PAIR_REJECTED' and decision['portfolio']['bets'] == 0
assert '0 errors, 0 warnings' in (ROOT/'pyright-explicit.log').read_text(encoding='utf-8')
summary = {
    'round':'IE-20260910', 'base':'a7ded8800536a2b9ad845ebdb9f3ee1758d97861',
    'created_at':datetime.now(UTC).isoformat(), 'python_unit':unit.attrib, 'python_redis':integration.attrib,
    'dotnet':counts, 'dotnet_coverage':coverage,
    'skips':[{'test':t.attrib['name'], 'reason':t.find('skipped').attrib['message']} for t in unit.iter('testcase') if t.find('skipped') is not None],
    'guard_tests':read(ROOT/'guard-boundaries/results.json'),
    'frozen_capture':{'fixture':'id1000032566887012','decision_at':'2026-09-11T23:00:00Z','collector_changed':False,'auditor_changed':False,'new_api_requests':0},
    'global_ready':False, 'profitability_established':False, 'real_capital_enabled':False,
}
(EVIDENCE/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
copies = {
    'runtime-04-final/receipt.json':'runtime-receipt.json',
    'runtime-04-final/python-integration.log':'python-redis.log',
    'runtime-04-final/python-junit.xml':'python-redis.xml',
    'runtime-04-final/dotnet-build.log':'dotnet-build.log',
    'runtime-04-final/dotnet-test.log':'dotnet-test.log',
    'runtime-01/dotnet-test.log':'before-runtime-smoke-failure.log',
    'runtime-02-diagnostic/dotnet-test.log':'before-intermittent-cross-pass.log',
    'runtime-03-fixed/dotnet-test.log':'before-bootstrap-failure.log',
    'cold-before/junit.xml':'before-cold-start.xml',
    'parser-before/junit.xml':'before-parser.xml',
    'cli-universe-before/junit.xml':'before-receipt-universe.xml',
    'unit-final/junit.xml':'python-unit.xml',
    'unit-final/isolation.json':'unit-isolation.json',
    'pyright-explicit.log':'pyright-explicit.log',
    'capture-experiment-02/decision.json':'decision.json',
    'capture-experiment-02/manifest.json':'capture-manifest.json',
    'capture-experiment-contract.json':'capture-contract.json',
    'software/redis-release-8.2.9.json':'redis-windows-release.json',
    'software/docker-redis-tag.json':'redis-container-tag.json',
    'CHECKPOINT_E_PROTOCOLO.md':'CHECKPOINT_E_PROTOCOLO.md',
}
for origin, target in copies.items():
    shutil.copyfile(ROOT/origin,EVIDENCE/target)
shutil.copyfile(next((ROOT/'runtime-04-final/dotnet-results').glob('*.trx')),EVIDENCE/'dotnet-tests.trx')
shutil.copyfile(next((ROOT/'runtime-04-final/dotnet-results').rglob('coverage.cobertura.xml')),EVIDENCE/'dotnet-coverage.xml')

write(DOC/'RESULTADO.md', '''
# Implementação IE-20260910

Foi corrigida a verificação do hotpath, implementado um consumidor offline de capturas e concluída a integração local Python/.NET/Redis com dados sintéticos. **Lucro líquido executável não foi demonstrado; o projeto não está globalmente pronto para operar.** Base main/a7ded88; trabalho solo em C:/BRASILEIRAO. Integração local, hashes e recuperação estão no recibo C:/BRASILEIRAO/AUDITORIA/IMPLEMENTACAO_2026-09-10.json.

## Correções entregues

O smoke importava o daemon após registrar um resultado com TTL de cinco segundos. Esse import inicializava NumPy/Numba e podia consumir a validade antes da verificação. Uma regressão temporal falhou antes. Antecipar o import foi uma correção intermediária; a solução final extraiu a validação para `kernel_message.py`, compartilhada pelo daemon e pelo smoke, sem iniciar cálculo, logging ou conexões. O símbolo antigo do daemon continua disponível. Uma segunda regressão comprova que a verificação não importa o runtime numérico. O parser também passou a rejeitar chaves JSON duplicadas, que antes podiam esconder valores contraditórios. Os contratos e os testes de mensagens válidas permanecem aprovados. A busca dos consumidores em código encontrou smoke e testes, sem dependência de coleta protegida; nenhum coletor foi editado.

O teste entre processos confundia inicialização de Python/JIT com recuperação de mensagens. O novo bootstrap sinaliza prontidão e espera uma barreira antes de assinar Pub/Sub. A requisição é registrada durante essa espera, mantendo a perda deliberada da notificação; somente depois o kernel é liberado para recuperar a fila. Os 40 segundos da verificação funcional, TTLs, identidade e critério de um único sinal foram preservados. O limite separado de inicialização é 120 segundos. O daemon operacional não ganhou barreiras de arquivos.

O novo comando `python -m brasileirao_predictor.research.price_strength.capture_decision` une contrato congelado, recibos, identidade, kickoff e o scanner já existente. Rejeita falhas HTTP/integridade, horários ambíguos, JSON inválido, pares inativos, timestamps empatados e capturas antigas. Um recibo posterior inválido impede recuperar um preço anterior favorável. Todos os arquivos salvos do fixture precisam ser fornecidos; tentativas fracassadas sem corpo também entram na revisão. Duas regressões adicionais detectaram e fecharam essas lacunas durante a implementação. Mesmo uma comparação sintética com EV condicional positivo termina em abstenção de execução enquanto faltarem evidências comerciais. Não foi adicionado executor financeiro.

Uma errata corrigiu 177 campos com mojibake no JSON dos registros RI, verificando reversibilidade da transformação. `REGISTROS_RI_UTF8.json` conserva as conclusões e a data da RI; `ERRATA_UTF8.json` registra cada alteração e hashes. Os bytes dos registros e manifestos congelados da RI não foram reescritos.

## Infraestrutura e validação

Docker/Podman não foram encontrados; o comando WSL informa que o componente não está instalado. O GET do MSI público Memurai foi recusado com MissingKey, sem contorno. A alternativa utilizada foi a distribuição comunitária redis-windows 8.2.9 MSYS2, ZIP sem serviço, cujo SHA256 foi confrontado com a release. Ela permite o ensaio local; não é homologação de Redis/Compose Linux em produção. [Release do distribuidor](https://github.com/redis-windows/redis-windows/releases/tag/8.2.9).

`tools/runtime_lab` inicia uma instância própria em 127.0.0.1:26380, comprova o PID Windows dono da porta antes de conectar, exige run_id e reserva DB14/15/13. Usa ambiente sem credenciais herdadas, perfis e temporários isolados, código .NET copiado, persistência desligada e encerramento do próprio processo no fim. Não instalou serviço, modificou firewall ou acessou Redis operacional. A barreira Python impede rede externa, porta6379, dados protegidos, SQLite externo, escrita externa e subprocessos arbitrários; uma falha na instalação da barreira encerra o Python. São controles de efeitos para testes inspecionados, não um sandbox contra código hostil arbitrário.

Resultado final: **282 testes Python aprovados e quatro pulos**, **27 testes Python com Redis real aprovados**, **110 testes .NET aprovados, zero pulos** e **sete ensaios de isolamento aprovados**. A cobertura .NET foi 86,58% de linhas e 82,39% de ramos, acima do critério existente de80%. Três pulos Python exigem subprocesso/Redis DB14 no harness unitário; um exige criação de symlink não permitida pelo host. Não foram contados como aprovados. O escopo não é a suíte integral nem a operação com dados reais. Antes/depois, logs, TRX e JUnit estão em `evidence`.

Ruff no escopo CI ampliado aos novos helpers e Pyright padrão/arquivos alterados foram verificados; build e conferência do wheel constam dos recibos finais. A CI foi configurada para deixar de pular a integração entre processos. Os serviços Redis de teste foram fixados no patch8.2.9 e no digest publicado no [Docker Hub](https://hub.docker.com/_/redis). Não houve push ou execução dessa nova CI remota; o Compose operacional permaneceu inalterado. Não atribuir o CI antigo da base às mudanças atuais.

## Experimento econômico desta rodada — 14 itens

1. **Pergunta:** as observações DC permitidas sustentam uma comparação de preços e decisão rastreável, mantendo os requisitos necessários à execução?
2. **Prioridade:** fechar admissão e integração antes de investir em outro modelo; nenhuma métrica preditiva substitui preço disponível.
3. **Hipótese/mecanismo:** um par API completo e contemporâneo poderia alimentar comparação condicional com referência Pinnacle. Isso não provaria disponibilidade pessoal, probabilidade verdadeira ou lucro.
4. **Experimento:** aplicar o consumidor às três capturas já congeladas, usando a última recebida até09/09/2026 20:17:30.413563UTC. É diagnóstico retrospectivo das observações, não a decisão T−60 de11/09. Protocolo e limites foram registrados antes da implementação; nenhuma variante foi escolhida por retorno. A repetição02 verifica a correção do consumidor, sem mudar parâmetros ou criar uma nova hipótese econômica.
5. **Dados/fontes:** recibo DC e capture_01/02/03, 585.080 bytes, três observações de um único fixture; identidade recuperada do catálogo/seleção previamente congelados e hash da seleção conferido. Nenhum label, odds autenticada nova ou desfecho foi consultado. Os177 históricos e o CSV2025 não foram reavaliados nesta rodada.
6. **Disponibilidade temporal:** latest-at-cutoff por received_at, max_age120s, max_skew15s; timestamps de mudança não viram clocks de publicação. As três colunas normalizadas representam a mesma disponibilidade local da resposta API e são explicitamente rotuladas assim. O cutoff futuro congelado, fixture e casas da rotina DC permanecem intactos.
7. **Resultado:** última resposta identificada, Pinnacle admitida no estado API, bet365.bet.br com bookmakerIsActive=false; o par foi rejeitado. Isso descreve coleta do agregador, não comprova suspensão comercial da casa. Resultado: uma abstenção no universo de um evento, zero candidatos comparáveis, zero apostas, stakes/exposição zero. A premissa de suficiência dos preços desse piloto perdeu suporte. Não existe amostra de três jogos independentes.
8. **Custos:** cenário explícito de2% por unidade e comissão hipotética0%, sem afirmar custos pessoais reais. Banca de demonstração100u permanece100u antes de custos fixos desconhecidos. PnL total, ROI sobre stakes e retorno após todos os custos são nulos/não mensuráveis. Não se declarou lucro zero ou positivo por ausência de apostas. O resultado condicional antigo de−9,24u permanece no histórico RI, sem nova otimização.
9. **Riscos:** falso sinal por preço não executável, referência correlacionada, revisão temporal, recusa, slippage, moeda/limites, seleção de variantes e custos operacionais desconhecidos.
10. **Limitações:** uma observação independente de fixture, ausência de aceite/capacidade/custos e de validação futura; o ensaio não mede rentabilidade. Testes sintéticos e infraestrutura funcionando não resolvem essas lacunas.
11. **Testes:** adversariais de estado/identidade/kickoff, todos os pais do preço, recibos inválidos e ausentes, ordem/tie de capturas, custo obrigatório, integridade/imutabilidade de saída e preservação de custos desconhecidos; integração real de processos separada da evidência econômica.
12. **Estado da evidência:** insuficiente; lucro executável não mensurável. A hipótese de suficiência destas três observações foi refutada neste escopo, sem concluir que nenhuma oportunidade futura exista.
13. **Decisão:** manter exposição zero e o consumidor como ferramenta offline; encerrar este experimento após a rejeição determinante, sem procurar um backtest positivo. A construção de outro modelo perdeu prioridade para obtenção de oferta admissível.
14. **Próxima informação decisiva:** recibo contemporâneo válido da captura DC já congelada, seguido de evidências independentes de disponibilidade, capacidade/moeda, custos e validação futura em protocolo próprio. Uma única captura válida ainda não demonstra lucro. O projeto não pode obter esses fatos por uma correção de código ou fabricando timestamps.

## Três estados e limites remanescentes

| Dimensão | Estado e escopo |
| --- | --- |
| Prontidão técnica | Pronto no laboratório testado: parser, consumidor offline e integração sintética Windows. Projeto globalmente não pronto; feed comercial/Compose operacional não homologados. |
| Admissibilidade dos dados | Capturas íntegras e admissíveis para diagnosticar o estado API recebido; insuficientes para comparação do par e inadmissíveis como prova de execução lucrativa. |
| Evidência econômica | Insuficiente; lucro líquido executável não mensurável. Nenhuma autorização financeira foi alterada. |

Continuam abertos os requisitos comerciais/temporais, a validação futura, o serving legado fora do novo caminho e a recuperação operacional protegida. H14/H15/H9/A1, seus avaliadores, observadores e dados não foram usados nem alterados. A rotina independente de11/09 permanece com fixture id1000032566887012, Pinnacle/bet365.bet.br e decisão23:00UTC; não foi acionada antecipadamente. Não há recibo followup nesta conferência. A configuração ativa da automação existente continua não confirmada por evidência legível; a cópia no caminho padrão do aplicativo também não foi encontrada. Não foi criada outra automação.

O maior avanço técnico foi demonstrar o caminho entre processos e retirar a inicialização numérica da verificação. A descoberta decisiva para o investimento econômico continua sendo a ausência de um par de preços admissível, não a qualidade de um modelo alternativo. [Reproduzir](REPRODUZIR.md) · [Registros atuais](REGISTROS.json) · [Próximo prompt](PROXIMO_PROMPT.md).
''')

write(DOC/'REPRODUZIR.md', r'''
# Reprodução IE-20260910

Executar somente em C:/BRASILEIRAO. O ambiente completo RI e SDK portátil existentes foram reutilizados; o venv mínimo PF e os helpers da captura permaneceram preservados. Python3.13.12, .NET SDK10.0.401 e versões do uv.lock. O laboratório é descartável e contém somente parâmetros fabricados; seus resultados não autorizam operação financeira.

## Integração Windows

O ZIP redis-windows8.2.9 está em work/implementacao-2026-09-10/software, SHA256 dcff676e861a4ae0a9854556239398e77a7469c9379af64a4a76798d166d1aa0, 12.336.427bytes. O executável tem SHA256 f9bf66f93438ec461b6e32453e6c9a8dde2f8c93c1018d1b75aa38b113ba3f14. Sua release/digests estão em evidence. Não instalar ou executar start.bat/serviço. A porta26380 deve estar livre; o runner recusa ocupação antes de conectar e não encerra servidores externos.

PowerShell, a partir de C:/BRASILEIRAO/brasileirao-predictor, escolhendo saída NOVA:

```powershell
& C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe -I tools/runtime_lab/run.py `
  --output C:/BRASILEIRAO/work/implementacao-2026-09-10/runtime-NOVO `
  --repo C:/BRASILEIRAO/brasileirao-predictor `
  --server C:/BRASILEIRAO/work/implementacao-2026-09-10/software/redis-8.2.9/Redis-8.2.9-Windows-x64-msys2/redis-server.exe `
  --server-sha256 f9bf66f93438ec461b6e32453e6c9a8dde2f8c93c1018d1b75aa38b113ba3f14 `
  --dotnet C:/BRASILEIRAO/work/revisao-integral-2026-09-09/dotnet-sdk/dotnet.exe `
  --nuget-cache C:/BRASILEIRAO/work/revisao-integral-2026-09-09/nuget-packages
```

O runner salva comandos, códigos de saída, PID/run_id, logs e TRX em receipt.json/arquivos locais. Reutiliza o cache NuGet RI; perfis e novos temporários ficam na nova saída. Nunca apontar ao Redis operacional. `--cross-only` delimita uma investigação de processo; não equivale ao lote completo. `--diagnostics` registra somente tipo/local de exceção do smoke sintético. O runner nativo exige Windows; a configuração CI usa Redis Linux e o mesmo bootstrap sintético, mas esta CI remota ainda não foi executada.

## Consumidor de capturas

CLI empacotada: `python -m brasileirao_predictor.research.price_strength.capture_decision --contract CONTRATO --receipt RECIBO --capture RAW1 --capture RAW2 --capture RAW3 --output-dir SAIDA_NOVA`. Todo arquivo salvo do fixture deve constar da lista; tentativas fracassadas sem corpo permanecem no universo via recibo. O contrato exige fixture, cinco identificadores positivos, kickoff, cutoff, banca de cenário e política de custos explícita. Exemplo efetivamente usado: evidence/capture-contract.json. `run_capture_experiment.py` na pasta work é a reprodução delimitada DC; preserva o hash do contrato e recebe um sufixo numérico novo de saída.

O comando não realiza GET, login, leitura automática de data/DB, inferência de caminhos de payload ou liquidação. O resultado sempre distingue comparação API condicional de execução. Manifestos fixam hashes dos bytes usados e do pacote de pesquisa, publicação sem sobrescrever outra saída. Não usar o cutoff do diagnóstico como substituto da captura futura congelada.

## Checks e escopo

`run_isolated.py` copiado da RI na pasta work recebe uma saída nova e uma lista explícita de testes. Lote final e pulos em evidence/summary.json. As tentativas anteriores e correções intermediárias permanecem em work; não remover falhas para apresentar aprovação limpa.

Ruff: `ruff check brasileirao_predictor brasileirao_scripts tests tools/runtime_lab` e `ruff format --check` no mesmo escopo. Pyright padrão mais configuração explícita em work/implementacao-2026-09-10/pyrightconfig.json; executar o Node local e o index.js da versão1.1.411, sem instalar latest. Build Python e smoke do wheel usam saídas novas dentro da rodada, sem DB/rede após construção. Backups finais: bundle Git verificado, clone bare/fsck e ZIP de evidências, descritos no recibo de auditoria. Não são restauração operacional de dados protegidos.
''')

write(DOC/'PROXIMO_PROMPT.md', '''
# Continuação após IE-20260910

Trabalhe sozinho e mantenha tudo em C:/BRASILEIRAO. Leia integralmente C:/BRASILEIRAO/INSTRUCOES/MANDATO_RECEBIDO_2026-09-09.txt e PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md. Confira main, git status, recibo IMPLEMENTACAO_2026-09-10.json, docs/ESTADO_ATUAL.md e o resultado IE antes de agir. Integração local não significa push, CI remota ou operação financeira.

Não reiniciar a revisão já feita, procurar um backtest positivo ou prometer lucro. Preserve H14/H15/H9/A1, outputs, agendas, claims e dependências de coleta. Não ler labels2026/coortes, executar avaliadores, abrir DB/Redis operacional, fazer compras/logins de apostas ou criar automações duplicadas. O pedido amplo de correção não revogou essas regras.

O parser puro, consumidor offline e integração entre processos foram implementados. Último lote local:282 Python/4pulos,27 Redis real,110.NET/0pulos e7barreiras. Confira recibos, wheel e hashes antes de reutilizar os números. Verificação local não homologou o Compose/feed comercial. O consumidor recebeu3capturas DC de1fixture e recusou o par; não existe lucro executável demonstrado.

Próxima entrada econômica: captura DC existente do fixture id1000032566887012, kickoff12/09/2026 00:00UTC, decisão11/09 23:00UTC, Pinnacle e bet365.bet.br. Consultar CONTINUIDADE DC e protocolo original para janela22:55–22:59:15UTC, alvo22:58:30UTC, limite deuma odds call, free250/reserva20, recibo/idempotência e auditoria. Não coletar antes, mudar fixture/corte ou buscar resultado. A automação conhecida completar-dados-do-brasileir-o pertence à tarefa01a08756-2962-7c43-9773-c790cc81329d; estado ativo não confirmado nesta rodada. Não duplicar nem presumir execução com base em TOML histórico.

Depois de uma captura admissível, ainda exigir oferta contemporânea, capacidade/moeda, custos reais e validação independente antes de alegar lucro. Esses requisitos estão abertos; uma única observação não basta. Prosseguir com trabalho autorizado que resolva uma dependência concreta; não fabricar precisão, timestamps ou execução.
''')

issues = [
    {'id':'IE01','problem':'Cold import durante TTL do resultado no smoke','before':'cold-before e parser-before falham; runtime01 falha intermitente compatível com janela curta','change':'Parser puro compartilhado; sem import numérico na verificação','status':'corrigido no escopo testado','evidence':'unit-final; runtime04'},
    {'id':'IE02','problem':'Chaves JSON duplicadas na invocação','before':'parser-before aceita valor contraditório anterior','change':'object_pairs_hook rejeita duplicatas antes de coerção','status':'corrigido','evidence':'parser-before; unit-final'},
    {'id':'IE03','problem':'Ausência de prova local Redis real/Python/.NET e CI pulando teste cross-process','change':'Instância própria por PID/run_id, barreiras, bootstrap e configuração CI; serviço de teste atualizado por digest','status':'validado localmente; CI remota pendente','evidence':'runtime04; guard-boundaries; ci.yml'},
    {'id':'IE04','problem':'Inicialização/JIT confundida com recuperação de notificação perdida','before':'runtime03 expira espera antes da prontidão','change':'Barreira de prontidão antes da medição, inscrição só após registro','status':'corrigido no harness; 110.NET aprovados','evidence':'runtime03; runtime04'},
    {'id':'IE05','problem':'Consumidor podia omitir falha sem payload ou captura salva mais recente','before':'Duas regressões cli-universe-before falham','change':'Universo de recibos completo, falhas preservadas e recusa de arquivos omitidos','status':'corrigido','evidence':'cli-universe-before; unit-final; capture-experiment02'},
    {'id':'IE06','problem':'Mojibake em177campos dos registros RI','change':'Sucessor UTF8 reversível; originais/hash preservados','status':'corrigido por errata, sem reescrever resultados','evidence':'ERRATA_UTF8.json'},
    {'id':'IE07','problem':'Ausência de preço/custos/capacidade/validação para lucro executável','change':'Diagnóstico real rejeita par e mantém exposição zero, custos desconhecidos explícitos','status':'dependência econômica externa aberta; hipótese de suficiência refutada neste piloto','evidence':'capture-experiment02; protocolo DC'},
]
(DOC/'REGISTROS.json').write_text(json.dumps({'round':'IE-20260910','base':summary['base'],'issues':issues,'states':{'technical':'ready_in_tested_lab_not_globally_ready','data':'insufficient_for_execution','economic':'executable_profit_not_measurable'},'previous_frozen_register':'../integral_review_2026-09-09/REGISTROS.json','previous_text_erratum':'REGISTROS_RI_UTF8.json'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

write(REPO/'docs/ESTADO_ATUAL.md', '''
# Estado atual — IE-20260910

**Implementação e integração local corrigidas no escopo testado; projeto globalmente não pronto; lucro líquido executável não demonstrado.** Trabalho solo em C:/BRASILEIRAO. [Resultado IE e14itens econômicos](continuation/implementation_2026-09-10/RESULTADO.md), [registros atuais](continuation/implementation_2026-09-10/REGISTROS.json), [reprodução](continuation/implementation_2026-09-10/REPRODUZIR.md) e [próximo prompt](continuation/implementation_2026-09-10/PROXIMO_PROMPT.md).

Base desta rodada main/a7ded8800536a2b9ad845ebdb9f3ee1758d97861. Commit final, estado Git, pacote e backups no recibo C:/BRASILEIRAO/AUDITORIA/IMPLEMENTACAO_2026-09-10.json. Não houve push, nova CI remota ou implantação operacional. A revisão RI anterior permanece congelada e acessível no histórico Git e em integral_review_2026-09-09.

O smoke agora usa um parser puro, comum ao daemon, sem inicializar NumPy/Numba para verificar uma resposta que pode expirar. Mensagens JSON com duplicatas são recusadas. O bootstrap do teste separa inicialização e recuperação de notificação perdida. O consumidor offline capture_decision exige identidade/kickoff e todo o universo de recibos, sem recuperar preços antigos favoráveis após falha posterior; comparação API não autoriza execução. A errata de177campos UTF8 mantém conclusões e bytes originais preservados.

Verificação local:282 testes Python aprovados/4pulos;27 testes Python com Redis real aprovados;110.NET aprovados/0pulos;7ensaios de isolamento aprovados. Cobertura .NET86,58%linhas/82,39%ramos. Ruff no escopo CI+helpers, Pyright e build/pacote foram verificados nos recibos. Três pulos Python exigem subprocesso/Redis no harness unitário e um exige symlink. Não é suíte integral nem prova econômica.

Ambiente completo RI preservado em work/revisao-integral-2026-09-09/venv e SDK10.0.401/dotnet-sdk; venv mínimo PF da captura inalterado. Novo laboratório em work/implementacao-2026-09-10, Redis8.2.9 comunitário Windows descartável na porta26380, DB14/15/13, PID/run_id conferidos e processo encerrado. Docker/Podman ausentes e WSL não instalado; Compose/feed comercial não homologados. CI de testes configurada com Redis8.2.9 por digest e cross-process habilitado, ainda sem execução remota.

Dados: as3capturas DC íntegras representam1fixture. À última resposta recebida em09/09 20:17:30.413563UTC, Pinnacle passou no estado API e bet365.bet.br estava sem coleta ativa pelo agregador; par rejeitado. Zero apostas/stakes/exposição,1abstenção; banca hipotética100u antes de custos fixos desconhecidos, PnL total e ROI não mensuráveis. Não houve coleta autenticada nova, label2026 ou otimização de retornos. Os177históricos,380jogos2025 e resultado condicional−9,24u continuam como evidência RI anterior, não um novo holdout.

H14/H15/H9/A1, DB/Redis operacional, observadores e agendas protegidos. Coletor e auditor DC conservam hashes; a captura fixa de11/09 decisão23:00UTC não foi acionada antecipadamente e não havia followup/receipt.json nesta conferência. Agenda completar-dados-do-brasileir-o não duplicada; estado atual não confirmado por resposta legível/localização no caminho padrão.

Os requisitos externos continuam sendo oferta contemporânea, referência admissível, capacidade/moeda, custos pessoais e validação futura. O serving legado não é o caminho financeiro; use a ferramenta isolada somente para auditoria/comparação condicional. Nenhuma operação de aposta foi implementada ou autorizada.
''')

write(REPO/'README.md', '''
# brasileirao-predictor

Pesquisa quantitativa e software para o Brasileirão Série A, em C:/BRASILEIRAO.

**Correções e integração local validadas; lucro executável ainda não demonstrado.** O projeto não está globalmente pronto para operação financeira. [Estado atual](docs/ESTADO_ATUAL.md) · [Resultado IE](docs/continuation/implementation_2026-09-10/RESULTADO.md) · [Reproduzir](docs/continuation/implementation_2026-09-10/REPRODUZIR.md).

## Implementação atual

O parser de mensagens do kernel é compartilhado e leve, recusando duplicatas JSON. O smoke verifica resultados sem iniciar NumPy/Numba e consumir sua validade durante o import. Um laboratório descartável comprova a integração Python/.NET/Redis, incluindo recuperação de notificação perdida e um único sinal para a requisição corrente.

O comando offline `python -m brasileirao_predictor.research.price_strength.capture_decision --help` audita arquivos explícitos de captura e recibo, exige identidade/kickoff congelados, preserva tentativas fracassadas e recusa preços antigos após um estado posterior inválido. Seu resultado separa comparação API condicional e execução; faltando evidência comercial, mantém abstenção. Não envia ordens ou liquida partidas.

Foram aprovados282 testes Python do escopo afetado,27 com Redis real,110.NET e7ensaios de isolamento. Quatro testes Python foram pulados com motivos registrados. [Logs, cobertura e limites](docs/continuation/implementation_2026-09-10/REPRODUZIR.md). Instalação, testes sintéticos e vantagem hipotética de preço não demonstram rentabilidade.

## Dados e continuidade

As3capturas permitidas de1fixture voltaram a ser rejeitadas como par API. Zero apostas/exposição; custos fixos e lucro líquido total seguem desconhecidos. A [revisão RI](docs/continuation/integral_review_2026-09-09/RESULTADO.md) preserva a auditoria dos177históricos,380jogos2025 e o resultado condicional negativo já conhecido, sem nova escolha de filtro.

Leia [registros atuais](docs/continuation/implementation_2026-09-10/REGISTROS.json), [mapa de dados](docs/DATA_MAP.md), [índice](docs/INDICE_DOCUMENTACAO.md), [retomada](docs/continuation/RETOMADA.md), [próximo prompt](docs/continuation/implementation_2026-09-10/PROXIMO_PROMPT.md) e [mandato](docs/continuation/MANDATO_LUCRO_2026-09-09.md). A errata UTF8 dos registros RI é sucessora, sem reescrever evidências congeladas.

H14/H15/H9/A1 permanecem protegidos. O [protocolo DC](docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md) conserva fixture, casas, janela e decisão de11/09 23:00UTC; a automação existente não foi duplicada. O serving legado, Compose operacional e feed comercial não estão homologados pelo laboratório. Código/entrega: C:/BRASILEIRAO/brasileirao-predictor e C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_IE_20260910.
''')

write(REPO/'docs/continuation/RETOMADA.md', '''
# Retomada após IE-20260910

Leia [próximo prompt](implementation_2026-09-10/PROXIMO_PROMPT.md), [estado](../ESTADO_ATUAL.md), [resultado](implementation_2026-09-10/RESULTADO.md), [registros](implementation_2026-09-10/REGISTROS.json) e o mandato original C:/BRASILEIRAO/INSTRUCOES/MANDATO_RECEBIDO_2026-09-09.txt. Trabalhe sozinho; toda escrita em C:/BRASILEIRAO.

Comece conferindo main/status, C:/BRASILEIRAO/AUDITORIA/IMPLEMENTACAO_2026-09-10.json, pacote e hashes dos helpers DC. Lote local282Python/4pulos,27Redis,110.NET/0pulos e7barreiras. O novo caminho offline abstém após par rejeitado; o lucro não está demonstrado. Não atribua a essas mudanças o CI remoto antigo.

O laboratório se encerrou sem serviço Redis permanente. Para repetir uma falha concreta, use tools/runtime_lab/run.py e saída nova, após conferir a porta26380 livre. Não iniciar Docker/Redis operacional, ler coortes, refazer backtest negativo com filtros escolhidos pelo resultado ou alterar agenda para completar métricas.

Próxima dependência econômica é a captura DC congelada e posterior admissão comercial/validação futura. Fixture id1000032566887012, kickoff12/09 00:00UTC, decisão11/09 23:00UTC, casas Pinnacle/bet365.bet.br, reserva20. Consulte integralmente CONTINUIDADE DC para janela e idempotência. H14/H15/H9/A1, seus resultados e observadores permanecem protegidos. Não duplicar a automação da tarefa anterior nem supor execução sem recibo.
''')
for file, heading, addition in [
    ('HANDOFF.md','# Handoff IE-20260910','Parser puro, consumidor offline e laboratório real integrados localmente.282Python/4pulos,27Redis,110.NET/0pulos e7barreiras; nenhuma rentabilidade demonstrada. Resultado e limites em docs/continuation/implementation_2026-09-10/RESULTADO.md. Recibo em C:/BRASILEIRAO/AUDITORIA/IMPLEMENTACAO_2026-09-10.json. Guias atuais atualizados; histórico RI abaixo preservado.'),
    ('docs/DATA_MAP.md','# Atualização de dados IE-20260910','Novo consumidor em brasileirao_predictor/research/price_strength/capture_decision.py. Diagnóstico controlado dos3payloads DC/1fixture no último recibo: par API rejeitado,1abstenção,zero apostas/exposição; PnL total desconhecido. Inputs/hash e saída em continuation/implementation_2026-09-10/evidence/capture-manifest.json e decision.json. Sem novos labels, coleta autenticada ou reutilização do CSV como holdout. Mapa histórico RI abaixo preservado.'),
    ('docs/INDICE_DOCUMENTACAO.md','# Índice atual IE-20260910','[Resultado](continuation/implementation_2026-09-10/RESULTADO.md), [registros](continuation/implementation_2026-09-10/REGISTROS.json), [reprodução](continuation/implementation_2026-09-10/REPRODUZIR.md), [próximo prompt](continuation/implementation_2026-09-10/PROXIMO_PROMPT.md), [errata UTF8](continuation/implementation_2026-09-10/ERRATA_UTF8.json) e [registros RI com texto corrigido](continuation/implementation_2026-09-10/REGISTROS_RI_UTF8.json). Últimos preservam datas/conclusões RI; não são novas avaliações. Índice anterior abaixo preservado.'),
]:
    path=REPO/file
    before=path.read_text(encoding='utf-8')
    if not before.startswith(heading):
        write(path,heading+'\n\n'+addition+'\n\n---\n\n'+before)
write(REPO/'tools/runtime_lab/README.md', '''
# Laboratório descartável

Ferramentas de desenvolvimento para Windows, separadas dos coletores e serviços. Iniciam apenas Redis explicitamente fornecido, com SHA256 fixado, em porta26380 livre, comprovam PID/run_id, testam dados sintéticos e encerram o processo. Não instalar serviço ou usar Redis operacional. A reprodução completa e limitações estão em docs/continuation/implementation_2026-09-10/REPRODUZIR.md.

Executar run.py com Python -I, argumentos explícitos e saída nova sob C:/BRASILEIRAO/work. sitecustomize/lab_guard são injetados somente nos processos do laboratório; não incluir essa pasta no PYTHONPATH de outros usos. kernel_synthetic aguarda a barreira do teste após imports/JIT, antes de assinar Pub/Sub. Os parâmetros são fabricados; não há DB de modelo. A configuração CI usa o mesmo bootstrap contra o Redis descartável do job. Nenhuma dessas ferramentas mede lucro ou comprova execução comercial.
''')
write(Path('C:/BRASILEIRAO/LEIA_PRIMEIRO.md'), '''
# BRASILEIRAO — leia primeiro

**IE-20260910: correções e integração local validadas; lucro líquido executável não demonstrado.** Projeto globalmente não pronto para operação financeira. Tudo permanece em C:/BRASILEIRAO.

- [Estado atual](brasileirao-predictor/docs/ESTADO_ATUAL.md).
- [Resultado e14itens econômicos](brasileirao-predictor/docs/continuation/implementation_2026-09-10/RESULTADO.md).
- [Registros atuais](brasileirao-predictor/docs/continuation/implementation_2026-09-10/REGISTROS.json) e [reprodução](brasileirao-predictor/docs/continuation/implementation_2026-09-10/REPRODUZIR.md).
- [Retomada](brasileirao-predictor/docs/continuation/RETOMADA.md) e [próximo prompt](INSTRUCOES/PROXIMO_PROMPT_APOS_IMPLEMENTACAO_2026-09-10.md).
- [Mandato original](INSTRUCOES/MANDATO_RECEBIDO_2026-09-09.txt) e [revisão RI preservada](brasileirao-predictor/docs/continuation/integral_review_2026-09-09/RESULTADO.md).

Entrega IE: ENTREGAS/BRASILEIRAO_IE_20260910. Integração, wheel e backups no recibo AUDITORIA/IMPLEMENTACAO_2026-09-10.json.282Python/4pulos,27Redis real,110.NET/0pulos e7barreiras. Par de preços DC rejeitado; nenhuma aposta ou nova avaliação de coorte. Captura futura e automação existente preservadas, sem antecipação/duplicação. Trabalho solo; conferir estado real e recibos antes de continuar.
''')
shutil.copyfile(DOC/'PROXIMO_PROMPT.md',Path('C:/BRASILEIRAO/INSTRUCOES/PROXIMO_PROMPT_APOS_IMPLEMENTACAO_2026-09-10.md'))
print(json.dumps({'docs_written':str(DOC),'tests_verified':True,'economic_state':decision['reason']}))
