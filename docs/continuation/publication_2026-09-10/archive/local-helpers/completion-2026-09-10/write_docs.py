"""Publish a dated successor; preserve historical research and all failed checks."""
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
docs=repo/'docs/continuation/completion_2026-09-10'
evidence=docs/'evidence'
stamp=datetime.now(UTC).isoformat()
coverage=json.loads((evidence/'coverage-summary.json').read_text(encoding='utf-8'))

# One current register for both claims and their associated defects/actions.
specs=[
('01','Exibição e registro usam a mesma previsão e data','predict.py / display.py','Duas chamadas e perda da data no formatter','from_prediction recebe resultado e mercado já registrados','validado','regressions-before; integrated-python-03','Teste sintético conta chamadas e confere data; não comprova PIT do banco'),
('02','Observações de protocolos e revisões distintos não se perdem','data/bitemporal_store.py','PK ignorava charter/event_at; hash arbitrava empate material','Chave inclui protocolo/evento; empate material recusado; filtro explícito de charter; schema legado recusado sem migrar','validado','regressions-before; pit-contracts-before; integrated-python-03','Banco novo isolado; migração operacional não executada'),
('03','Cobertura Sportmonks inclui todas as páginas autorizadas','data/sportmonks_provider.py','Primeira página ou metadata ausente eram tratadas como coleção completa','Cursor/legado, orçamento explícito, rejeição de incompletude e cursor repetido; next_page externo ignorado','validado','pagination-before; integrated-python-03; sources/receipts.json','Contrato sintético e documentação atual; nenhuma consulta autenticada'),
('04','Faixa configurada de edge prova confiança alta','display.py','Interface afirmava ALTA e validação lucrativa sem evidência correspondente','Confiança NÃO VALIDADA, preços diagnósticos, capital false e comentários corrigidos','validado','confidence-before; integrated-python-03','Premissa refutada; não altera métricas históricas'),
('05','Escalação recebida depois do corte pode entrar por ter publicação anterior','research/residual_features.py','Ausência de checagem de ingestão; empate arbitrário de vintages','Exige ingestão até corte e recusa versões conflitantes no mesmo recibo','validado','source-regressions-before; integrated-python-03','Extrator de linhas; envelope vazio/revisões e imputação do pipeline legado continuam fora da admissão econômica'),
('06','published_at da API-Football equivale ao relógio local','data/api_football_provider.py','Inventava publicação antes da requisição e ecoava erro arbitrário da fonte','published_at=null; recebido após resposta; erro sanitizado; esquema lineup/2','validado','source-regressions-before; integrated-python-03','Publicação real continua desconhecida; erro HTTP da documentação não prova indisponibilidade da API'),
('07','Sportmonks starting_at sem sufixo é necessariamente inválido','data/sportmonks_provider.py','Descartava data que o contrato retorna no fuso da requisição','Requisição fixa timezone=UTC e conversão sob esse contrato','validado','source-regressions-before; sources-followup/receipts.json; integrated-python-03','UTC confirmado na documentação primária; campos de disponibilidade comercial não existem neste adaptador'),
('08','Consenso pode avaliar a própria casa e combinar capturas','data/market_anchor.py','Mistura de eventos/linhas, vintages e seleção duplicada; ofertante na referência','Identidade única, captura única, conflito recusado, offered_by excluído da referência; método/v2','validado','anchor-period-before; integrated-python-03','Diagnóstico; best_odds observado não é oferta executável; persist_market_observations compartilhado permaneceu igual'),
('09','Adaptador legado The Odds API admite apenas recebimento pré-jogo','data/the_odds_api_provider.py; data/odds_api_snapshot.py','Teste sintético reproduz PROSPECTIVE_ELIGIBLE após kickoff no legado compartilhado','Legado protegido preservado; sucessor offline guarda SHA, IDs, clocks, vazio/inválido/incompleto, ABSTAIN e capital false','validado','odds-receipt-tests; integrated-python-03; package-smoke','Sucessor independente disponível; integração no coletor H9 não realizada nem autorizada'),
('10','NB do total é a mesma NB das contagens individuais','event_models.py','CDF do total não correspondia à soma de duas NB ajustadas; entradas/fallbacks inválidos aceitos','Convolução individual, contagens/feature finitas obrigatórias, distribuição coerente e fallback identificado','validado','math-consumer-before; event-inputs-before; integrated-python-03','Sem novo fit em dados reais ou reavaliação de lucro'),
('11','Qualquer grade numérica e linha produz mercado válido','market_pricer.py','Aceitava NaN, massas negativas/não normalizadas e linha não implementada','Probabilidade quadrada normalizada; AH em quartos; total inteiro/meio; placar inteiro','validado','math-consumer-before; pit-contracts-before; integrated-python-03','OU de quarto não implementado e agora recusado'),
('12','Contrato live impede placar negativo e mesmo clube nos dois lados','prediction_protocol.py','Placar negativo passava pela prontidão','Validação de contagens não negativas e times distintos','validado','math-consumer-before; integrated-python-03','Prontidão continua baseada em declarações do chamador, não autentica a procedência do modelo ou dados'),
('13','CLI de previsão registra toda previsão que exibe','brasileirao_scripts/prever.py','Recalculava; ignorava falha de log; período usava cache e caminho diferentes','Fluxos usam build/show comuns, data preservada; falha de registro interrompe também período','validado','math-consumer-before; anchor-period-before; integrated-python-03','Cache compartilhado continua legado e exploratório; fonte comercial não admitida'),
('14','Livro manual valida valores e associa liquidação por identidade','bet_log.py','NaN/Inf/bool, ID duplicado, HT impossível; banca/lista associavam pela posição','Validações antes de append, IDs estáveis, capital disponível separado da exposição','validado','ledger-before; ledger-after; integrated-python-03','Unidades brutas atuais; custos/câmbio não reconciliados; journal manual não é ledger de execução certificado'),
('15','Consulta de previsão abre armazenamento sem permissão de escrita','predict.py','build abria conexão RW','db.connect read_only=True no consumidor, sem alterar db compartilhado','validado','serving-storage-before; serving-storage-after; integrated-python-03','Banco sintético; nenhum banco operacional aberto'),
('16','Log aceita os mesmos parâmetros que o motor','prediction_log.py','Assumia tupla de cinco; quatro valores/dict falhavam','Aceita quatro/cinco/dict, conserva parâmetros sem arredondar e valida JSON antes de criar saída','validado','serving-storage-before; integrated-python-03','Log não substitui artefato imutável de treinamento/revisões'),
('17','Filtro SQL temporal e concentração são invariantes ao formato','data/pit_backfill.py','Comparação lexical de offsets, HHI dividido por jogos e bootstrap não finito','Corte normalizado UTC, HHI por aparições, bootstrap finito e raw criado exclusivamente','validado','pit-contracts-before; integrated-python-03','Curated legado continua latest-state; não reconstruir revisões antigas ou closing executável com esse schema'),
('18','Kelly e recibo .NET são válidos nas bordas','MarketStateEngine.cs; KernelContracts.cs','Stake negativa, entradas não finitas, fair odd inválida e recibo futuro aceitos','Kelly em domínio válido com piso zero; configuração validada; odd finita; futuro não fresco','validado','runtime-before; runtime-after-02; runtime-cross-diagnostic','119 casos únicos passaram entre execuções; não houve suíte completa final sem falha intermitente'),
('19','Sinal Redis e T0 provam execução/publicação','LatencyRecord.cs','Nomes sugeriam publicação comprovada e recomendação financeira','BetSignal explicita simulação/capital false; T0 declara captura não verificada, SourcePublishedAt=null','validado','runtime-after-02; runtime-cross-diagnostic','Não certifica aceitação, liquidez ou modelo; sem ordens'),
('20','Inicializador Compose é seguro ao reencontrar volumes','init_compose_data.py; compose.yaml','Poderia sobrescrever parâmetros existentes; data fixa parecia instante real','Recusa destinos existentes/iguais, reserva exclusiva, relógio atual, aviso de parâmetros demo; Redis alinhado ao digest CI','validado','compose-init-before; storage-final','Init sintético; Docker/Compose não executado neste Windows'),
('21','Teste cross-process é estável no ambiente local','tools/runtime_lab/kernel_synthetic.py','runtime-after-02 excedeu inicialização; log da causa não existia','Instrumentação por fase e stack aos45s; repetição isolada passou em24s','em investigação','runtime-after-02; runtime-cross-diagnostic','Causa da falha anterior não determinada; passar na repetição não prova estabilidade operacional'),
('22','Serving legado prova artefato imutável e histórico conhecido','db.py; ratings.py; cron_update_models.py; model.py; xg_model.py','Cache por contagem/config; escrita separada Elo/params; placar revisado conserva primeiro relógio; xG/proveniência incompletos','Dependências protegidas preservadas e retiradas do caminho de validação econômica; usar contratos independentes','bloqueado','boundary-check.json; MAPA_SISTEMA.md','Mudança exige separação comprovada das coortes; não alterar coleta protegida'),
('23','Feed comercial e worker representam modelo/feed efetivos','MarketOddsCache.cs; Worker.cs; docker/','Endpoint de exemplo, Elo1500 fixo, posição UNKNOWN e parâmetros de demonstração','Estado experimental explícito; sinal financeiro sempre simulado; homologação comercial não afirmada','bloqueado','MAPA_SISTEMA.md; testes .NET','Necessários fornecedor, contrato, IDs/revisões/estado e artefato admissível; plano/custo não confirmados'),
('24','Agendamento configurado prova tarefa ativa e execução futura','Automação completar-dados-do-brasileir-o','Ferramenta view só devolve cartão de UI; configuração documental não prova ativo','Consulta somente leitura preservada; não duplicar, não antecipar captura','não verificado','automation-view.json; continuidade DC','Depende de estado legível no aplicativo e recibo de execução na janela'),
('25','Todo arquivo inventariado foi lido semanticamente','Inventários RI/CPL','Inventário/estática foram confundidos com revisão integral anterior','Ledger distingue78 leituras semânticas,314 análises estáticas/pontuais e58 contratos protegidos','identificado','source-inventory.json; coverage-summary.json','Não declarar leitura semântica de450 arquivos nem encerramento integral do mandato'),
('26','Máximos BE já podem virar lucro executável','BE-P02; pergunta principal CPL','Casas/timestamps/aceitação/capacidade continuam ausentes','Contratos/decoder melhorados; sete GETs documentais, sem nova cotação nem novo desempenho','bloqueado','MAPA_DADOS.md; RESULTADO.md; recibos fontes','Preço nominal simultâneo e condições comerciais/fills/custos são a próxima dependência'),
]
claims=[]; issues=[]
for num,claim,scope,cause,action,status,proof,limit in specs:
    claimid='CPL-A'+num; issueid='CPL-P'+num
    conclusion='refutada na versão anterior; corrigida no escopo dos testes' if status=='validado' else 'parcialmente confirmada' if num=='21' else 'não verificada ou não verificável no escopo atual'
    claims.append(dict(id=claimid,claim=claim,origin='Inspeção CPL, 10/09/2026',scope=scope,required='Contrato e reprodução verificável conforme problema associado',found=cause+'; '+action,evidence=proof,conclusion=conclusion,impact=limit,issue=issueid))
    normalized='bloqueado' if status=='não verificado' else status
    issues.append(dict(id=issueid,claim=claimid,problem=cause,type='software/contrato' if int(num)<=20 else 'operação/evidência/cobertura',severity='alta' if int(num)!=25 else 'média',dependencies=scope,action=action,closure_test=proof,status=normalized,limitation=limit))
register=dict(round='CPL-20260910',dated_at=stamp,base='456b9025cfa3a596e754088ec3001fbeb5fcc7de',claims=claims,issues=issues,
    predecessors=['../implementation_2026-09-10/REGISTROS_RI_UTF8.json','../implementation_2026-09-10/REGISTROS.json','../economic_search_2026-09-10/REGISTROS.json'],
    states=dict(technical='pronto apenas nos contratos corrigidos e ensaios descritos; sistema global não pronto',data='parciais e insuficientes para execução comercial',economic='lucro executável não mensurável; candidato BE somente para investigação',mandate='em andamento; cobertura semântica integral não demonstrada'))
(docs/'REGISTROS.json').write_text(json.dumps(register,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
table=['# Registros atuais CPL-20260910','', 'Fonte única: [REGISTROS.json](REGISTROS.json). Alegações e problemas são cruzados pelo mesmo sufixo. O estado abaixo é gerado desse registro, não uma segunda lista independente.','', '| Problema | Alegação afetada | Ação | Estado | Limite |','| --- | --- | --- | --- | --- |']
for s in specs:
    n,c,_,_,a,status,_,lim=s
    table.append(f'| CPL-P{n} / A{n} | {c} | {a} | {status} | {lim} |')
(docs/'REGISTROS.md').write_text('\n'.join(table)+'\n',encoding='utf-8')

(docs/'RESULTADO.md').write_text('''# CPL-20260910 — correções, dados e validação delimitada

Foram corrigidos e testados contratos de previsão, temporalidade, preços, contabilidade e infraestrutura. **O projeto não foi entregue lucrando. A revisão semântica integral ainda não está demonstrada.** O mandato continua aberto; esta entrega fixa código e evidências para prosseguir sem perder trabalho ou transformar um checkpoint em conclusão global.

Os [registros centrais](REGISTROS.md) ligam cada alegação à falha, ação, teste e limite. A base foi main/456b9025cfa3a596e754088ec3001fbeb5fcc7de. Trabalho solo, em C:/BRASILEIRAO. Nenhuma aposta, ordem, autenticação de conta de apostas, API limitada ou consulta de resultados das coortes nesta rodada. H14/H15/H9/A1 e dependências compartilhadas identificadas foram preservadas; ver evidence/boundary-check.json.

## Validação e três estados

- Técnica: **pronto no escopo dos contratos corrigidos; sistema global não pronto**.196 testes Python passaram:192 integrados,3 do inicializador e1 adicional de schema legado.27 testes com Redis real passaram.119 casos .NET únicos passaram em execuções separadas: o último lote completo teve118 passagens e1 falha de inicialização; o caso restante passou isoladamente depois da instrumentação. A causa da falha intermitente continua desconhecida. Não reportar119/119 numa única execução final.
- Dados: **parciais/insuficientes para lucro executável**. Sete GETs públicos documentais nesta rodada; cinco respostas200, das quais uma era Page Not Found. Duas falhas na API-Football, a segunda403. Nenhum preço novo recuperado, nenhum label novo acessado. Raw documental, URLs, horários, bytes e hashes preservados.
- Economia: **não mensurável para execução real**. BE conserva um candidato de preços condicionado, sem casa/horário/fill comprovados. Não houve nova performance, mudança de stake ou ajuste para obter saldo favorável.

Ruff/formato e Pyright verificam o conjunto alterado; build, instalação de wheel, CLI, manifesto e recuperação Git constam dos recibos finais. Falhas anteriores e recusas das barreiras de isolamento permanecem na entrega. Testes tentaram caminhos legados de SQLite e leitura de cache: o runner recusou antes do acesso; isso não foi acesso operacional nem prova de que o legado fosse isolado por si só.

Inventário450 arquivos:78 com leitura semântica registrada nesta continuação,314 com análise estática/pontual e58 sob contrato protegido. Essa discriminação corrige a alegação anterior de revisão completa. A profundidade por arquivo está no inventário; ainda não representa semântica integral de todos os arquivos. Módulo serving_evaluator contém classe H9 junto de código legado e foi reclassificado como misto protegido; nenhum avaliador/coorte foi executado.

## Rodada econômica:14 itens

1. **Pergunta:** o envelope BE pode virar observação nominal, simultânea e utilizável sem confundir recibo com execução?
2. **Prioridade:** procedência do preço e preenchimento mudam mais a decisão que outro modelo ajustado aos mesmos anos.
3. **Hipótese/mecanismo:** carteira dos três resultados pode ter sobra se todas as pernas estiverem realmente disponíveis nas condições usadas. A simultaneidade/aceitação não está demonstrada.
4. **Experimento:** investigação documental e implementação de contratos, limitada previamente a12 GETs públicos;7 realizados. Não houve teste novo de retornos. A conta BE ficou congelada.
5. **Dados/fontes:** CSV e177 históricos já íntegros não foram repetidos. Fontes primárias The Odds API e Sportmonks recuperadas; API-Football documental bloqueada. Ver [mapa](MAPA_DADOS.md).
6. **Disponibilidade temporal:** received/observed/published/changed/decision separados. Publicação desconhecida é null. Nova leitura nunca comprova disponibilidade passada. O decoder conserva vazio/inválido e abstém.
7. **Resultado:** nenhuma nova oferta nominal recuperada;0 apostas e0 exposição nesta rodada. Resultado BE permanece histórico:226 carteiras hipotéticas,+4,6376u; modelo de gols−99,60u. Não são resultados CPL nem garantia futura.
8. **Custos:**0 chamadas autenticadas/limitadas. Custos pessoais, capacidade, moeda e infraestrutura atribuível desconhecidos; PnL líquido total e ROI executável não mensuráveis. Não assumir zero para esses custos.
9. **Riscos:** preenchimento parcial, revisão/suspensão, identidade incorreta, relógios incompletos, múltiplas tentativas, concentração e uso retrospectivo de máximos. As sensibilidades BE são hipóteses preservadas, não taxas observadas.
10. **Limitações:** sem histórico nominal simultâneo, limite pessoal ou aceite; módulos legados e Compose/feed comercial não homologados; cobertura semântica geral ainda parcial; coortes protegidas fora da execução.
11. **Testes:** regressões sintéticas antes/depois, contratos de fonte, cortes UTC, cálculo de probabilidades, banca por ID, leitura RO, logs, .NET/Redis, build/CLI e cópia/restauração. Testes de software não substituem evidência de mercado.
12. **Estado da evidência:** suficiente para confiar somente nos contratos demonstrados; insuficiente para admitir operação ou rentabilidade. Hipótese de suficiência da infraestrutura refutada; oportunidade comercial ainda não mensurável.
13. **Decisão:** manter candidato BE para investigação de preço nominal; modelo de gols reprovado permanece sem prioridade; nenhum novo tuning, capital ou observador. Não modificar captura DC para acomodar o candidato de três pernas.
14. **Próxima informação decisiva:** preços identificados simultâneos, seus estados/revisões e condições verificáveis para preencher as três pernas, seguidos de protocolo futuro separado. A captura DC de11/09 23:00UTC testa somente a dupla congelada e não valida essa carteira.

A descoberta que mais muda a decisão é que havia falhas concretas capazes de alterar odds/probabilidades/contabilidade e de exagerar a confiança exibida. Corrigi-las torna a decisão mais fiel aos dados; não cria, por si, uma oferta rentável. A hipótese que perdeu prioridade continua sendo recuperar lucro retunando o modelo de gols já reprovado.

## Continuação necessária

Prosseguir pelos itens abertos CPL-P21–26 e pelo [próximo prompt](PROXIMO_PROMPT.md). Não repetir testes já aprovados sem mudança ou falha concreta. Não modificar dependências protegidas para fechar checklist. Não declarar o mandato integralmente concluído enquanto a cobertura não estiver demonstrada e houver trabalho necessário viável.

Código integrado, hashes e backups: C:/BRASILEIRAO/AUDITORIA/CONTINUACAO_INTEGRAL_2026-09-10.json. A restauração da entrega de código/evidência não é restauração operacional de bancos/coortes protegidos.
''',encoding='utf-8')

(docs/'MAPA_SISTEMA.md').write_text('''# Mapa real e decisões CPL

| Subsistema/caminhos | Entradas → saídas / consumidores | Estado e decisão | Evidência/limite |
| --- | --- | --- | --- |
| ingest, Sofascore/FBref, db, ratings, cron_update_models, model/xg | Resultados/estatísticas → DB/Elo/parâmetros → serving e pesquisa | Legado compartilhado preservado; fora da validação econômica | Revisões podem herdar relógio; cache por contagem não prova conteúdo; restauração operacional vedada |
| predict, display, prever, prediction_log | Modelo+consulta agregada → diagnóstico e log | Corrigidos RO, cálculo único, data, parâmetros/log obrigatório; uso exploratório |196 testes Python delimitados; prontidão declarada não é procedência autenticada |
| event_models, dixon_coles, market_pricer, simulator | Contagens/grade → probabilidades/settlement sintético | Convolução NB e contratos de massa/linha corrigidos; sem retuning | Histórico de eventos sem features PIT completas não admite evidência econômica |
| data/api_football_provider, sportmonks_provider | Resposta opt-in → linhas shadow | Publicação desconhecida, UTC e paginação corrigidos | Adaptadores de cobertura; sem coleta autenticada/recibo real novo |
| data/the_odds_api_provider | API → observações usadas também pelo H9 | Preservado; sucessor separado necessário | Legado aceita pós-kickoff como elegível no teste; não promovido |
| data/odds_api_snapshot | Raw explícito+SHA+recibo → envelope completo/vazio/inválido, ABSTAIN | Novo consumidor puro e CLI | Sem rede, DB, credenciais ou execução; pacote/CLI verificados |
| bitemporal_store, pit_backfill | Observações com clocks → consulta por corte/charter | Conflitos/PK, UTC, bootstrap/HHI e raw exclusivo corrigidos | Banco antigo não é migrado automaticamente; curated latest-state não conserva todas as revisões |
| bookmaker_odds, market_anchor, lineup_archive/residual_features | Snapshots/linhas → diagnóstico/feature | Referência independente opcional e vintages de escalação corrigidos | Arquivo plano de escalações não preserva envelope vazio; imputações legadas não certificadas. Fora do caminho econômico escolhido |
| bet_log, settle | Relato manual → liquidação/lista/banca brutas | ID e valores corrigidos; manter manual/experimental | Não reconcilia custos reais, câmbio, unidade histórica ou concorrência de journal; não é ledger de apostas aceitas |
| research/price_strength, economic_search | Arquivos explícitos e protocolos → pesquisa/abstenção/artefatos | Caminho econômico independente mantido; BE congelado | Não usa model/DB operacional; nova pesquisa exige protocolo prévio; não rodar study com coortes |
| Demais research e brasileirao_scripts de experimentos | Bases/folds/config históricos → relatórios | Exploratórios/congelados; manter histórico fora da decisão ativa | Inventário/estática e leitura pontual, sem afirmar revisão semântica de cada script nem reabrir seus resultados |
| Worker/.NET/VORP/MarketOddsCache | Inbox Redis+artefatos+feed exemplo → estado/kernel/sinal | Protocolo testado; feed/modelo comerciais não homologados | Elo1500 fixo, posição UNKNOWN, fallback VORP/default; não fornecem validade econômica |
| MarketStateEngine/KernelContracts/LatencyRecord | Odds modelo/mercado → sinal simulado | Domínio Kelly/finitude/futuro e rotulagem corrigidos; unsubscribe na parada |119 casos únicos em execuções separadas; instabilidade de inicialização permanece |
| kernel_daemon/kernel_message/kernel_redis_v2 | Request com identidade/fence → fair odds/ready | IE preservado, integração exercitada |27 Redis;1 cross-process final passou; bootstrap instrumentado |
| Dockerfiles/compose/init_compose_data | Build+config+volumes → demo kernel/worker | Init recusa volumes; imagem Redis alinhada à CI por digest | Sem Docker/Podman instalado; Compose não executado; Windows Redis comunitário não homologa imagem Linux |
| packaging/CI/.NET csproj/uv.lock | Fontes/deps fixadas → wheel/sdist/binários | Build local e instalação específica; CI histórica separada | SDK/Python/deps C:/BRASILEIRAO; Git, PowerShell, Windows e Codex são dependências externas inevitáveis |
| backup_restore e migração | SQLite/arquivos → backup/restauração | Implementação inspecionada; operação protegida não executada | Entrega Git/ZIP é verificada separadamente; não confundir com restauração dos5 snapshots operacionais |
| ecosystem_plugin | Metadados → registro de domínio | Adapter parcial; health WAITING/sem promoção | Capabilities descritivas não provam execução de jobs |
| H14/H15/H9/A1, governança, operacional_readiness, serving_evaluator misto | Contratos/metadados protegidos | Preservados; sem execução/renovação/settlement |58 arquivos delimitados; funções _canon/_market_probs/persist_market_observations inalteradas por AST |
| Automação DC e helpers externos ao Git | Janela congelada → tentativa/recibo futuro | Preservados e não duplicados | UI view sem estado legível; SHA helpers conferido; sucesso futuro depende de recibo |

O inventário por arquivo registra SHA, tamanho, profundidade efetiva e import contracts iniciais. Não há frontend web de aplicação encontrado no inventário; a interface existente é CLI/JSON. A decisão de manter módulos antigos fora do caminho econômico não apaga seus defeitos ou equivale a validá-los. A cobertura semântica adicional permanece trabalho de continuação.

Benefício das correções: rejeitar dados/estados inválidos antes da decisão e impedir apresentação de diagnóstico como prontidão financeira. Alternativa rejeitada: alterar coletores compartilhados ou reavaliar coortes para fechar a revisão, porque violaria o mandato. Sucessor puro e testes sintéticos fornecem a correção utilizável sem mudar a coleta protegida.
''',encoding='utf-8')

(docs/'MAPA_DADOS.md').write_text('''# Fontes, campos e lacunas CPL

| Conjunto/fonte | Local/versão/semântica | Situação para a finalidade |
| --- | --- | --- |
| CSV Football-Data 2012–2024/BE | public_sources/football_data_bra_origin_csv.csv em work/data-completion-2026-09-09; Season/Date/Home/Away/FTHG/FTAG/PSC/MaxC; placar é label, preço decimal, máximo anônimo |4.940 jogos e4.939 trios calculáveis conferidos em BE; nenhum novo download/label. Cenário exploratório; inadequado para simultaneidade/aceite |
|177 timelines OddsPapi/DC | raw/Jan–Jun2026; fixture/participantes/torneio/season, bookmaker/selection, changedAt e recibo de aquisição |623.271.596B previamente íntegros; recebidos depois das decisões. Integridade não prova PIT; nenhum novo join de desfecho |
|3 capturas DC/1 fixture | prospective_pilot; última09/09 20:17:30.413563UTC; identidade congelada | Par API anteriormente rejeitado; estado comercial desconhecido. Não repetir piloto para fabricar amostra |
| Captura futura DC | decisão11/09 23:00UTC; kickoff12/09 00:00UTC; Pinnacle/bet365.bet.br | Dependente da coleta futura na janela; reserva20, quota/idempotência e helpers intocados |
| The Odds API v4 | https://the-odds-api.com/liveapi/guides/v4/; docs200; raw/hash em sources | Confirma endpoints/mercados/clocks; paid historical exige plano/quotas. Nenhuma chamada autenticada; históricos nominais ainda ausentes |
| Sportmonks paginação | https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/introduction/pagination.md | Cursor atual/has_more; cada página consome consulta; per_page não acompanha cursor. Código agora respeita orçamento e desconhece completude sem metadata |
| Sportmonks request/UTC | https://docs.sportmonks.com/v3/welcome/making-your-first-request.md e https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/introduction/set-your-time-zone.md | UTC padrão e parâmetro timezone confirmados. Raw timezone3731B SHA d0e7dc228de208a555ff3d89e173dafac415d760d6e2fb6aa1d5b07b81cf51ba. URL anterior timezones.md retornou200/Page Not Found; não contar como evidência |
| API-Football | documentation-v3 HTTPError sem status salvo no primeiro helper; guia oficial alternativo HTTP403 | Limitação do recibo antigo mantida. Não inventar o status faltante; não contornar bloqueio. Recebimento local não é publicação |
| Novo envelope Odds API | brasileirao_predictor/data/odds_api_snapshot.py; source_event_id, sport, home/away, bookmaker, market/line/selection/price, changed/received/published | Estrutura/identidade/hash testados; vazio/inválido preservados. published=null e comercial UNKNOWN; execução ABSTAIN. Não está integrado a H9 |
| Bitemporal | charter+entity+source+event/published/ingested+payload hash | Clocks UTC, versões em empate recusadas. Novo schema; schema anterior exige migração isolada explícita, não automática |
| Arquivos operacionais preservados | C:/BRASILEIRAO/DADOS_PRESERVADOS | Só metadados/contratos permitidos; nenhum conteúdo usado para pesquisa/validação CPL |

Campos de resultado entram apenas como labels nos estudos autorizados; suas revisões exigem recibo próprio. Features de escalação exigem ingestão antes do corte e vintage compatível. Preços agregados do serving ainda se associam aproximadamente por nome/data; não substituem IDs e oferta contemporânea. Ausência, suspensão e resposta inválida não autorizam recuperar uma cotação anterior favorável. Custos, limites, moeda, liquidez e capacidade desconhecidos permanecem desconhecidos.

Recuperação:7 GETs documentais diretos dentro do orçamento12; nenhuma cotação nova, API limitada, login, pagamento ou consumo da reserva. Os antigos bloqueios OddsPortal/Betfair em BE continuam registrados, sem repetição idêntica. Documentação foi integrada aos contratos/testes; não foi fabricada uma série de preços com base em exemplos.

Dependência decisiva: observação nominal simultânea e condições de preenchimento/custo. Os recursos atuais não estabelecem esse requisito. Sem ele, a conclusão de lucro executável continua impedida. A documentação [Scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app) não verifica o estado particular da automação; a consulta do aplicativo só produziu cartão de UI.
''',encoding='utf-8')

(docs/'PROXIMO_PROMPT.md').write_text('''Leia integralmente o mandato original e PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md em C:/BRASILEIRAO/INSTRUCOES. Continue sozinho, sem agentes, em C:/BRASILEIRAO/brasileirao-predictor. Este checkpoint não encerra o mandato.

Confira HEAD/status e AUDITORIA/CONTINUACAO_INTEGRAL_2026-09-10.json. Leia RESULTADO.md, REGISTROS.json, MAPA_SISTEMA.md, MAPA_DADOS.md e evidence/source-inventory.json desta pasta. Preserve RI/IE/BE, falhas/testes e dados congelados. Não trate450 arquivos inventariados como450 revisados semanticamente; a leitura registrada nesta continuação é78. Amplie a cobertura semântica dos demais componentes relevantes por impacto, mantendo rastreabilidade. Não refaça leituras/testes aprovados sem causa.

Prioridades abertas: completar cobertura demonstrável; investigar nova reprodução da instabilidade de cold-start com os logs de fases, sem aumentar timeout para mascarar falha; decidir sucessores isolados para schema latest-state/lineups e cache compartilhado apenas se necessários ao caminho econômico, sem modificar dependências de coleta protegida. O livro manual continua bruto e não certifica custos/câmbio/concorrência. Feed comercial é exemplo e Worker usa Elo1500/posiçãoUNKNOWN; não habilitar capital ou afirmar modelo homologado.

Os196 testes Python e119 casos.NET únicos passaram em execuções separadas; o último lote.NET completo teve118 passes/1falha e o caso passou depois isoladamente. Não reescrever isso como uma suíte final única perfeita. Ruff/Pyright/build/CLI/restauração devem ser conferidos nos recibos, junto do commit.

Economia: BE congelado,226 envelopes anônimos hipotéticos positivos e modelo de gols reprovado; não retunar para salvar saldo. Pergunta principal é recuperar oferta nominal/simultânea e dados de preenchimento/custos. Nenhuma nova performance CPL. Novas capturas/estudos exigem protocolo anterior e plano/quota/reservas confirmados. Fonte documental API-Football403 não autoriza bypass. Não repetir lotes íntegros.

H14/H15/H9/A1, resultados, avaliadores, agendas, claims e dependências protegidos. Não ler resultados intermediários, liquidar, executar avaliadores, renovar claims nem usar como holdout. serving_evaluator é módulo misto protegido. Não alterar db/ratings/cron/model/xg/TheOddsApi legado/bookmaker_stability para fechar checklist. Funções compartilhadas _canon/_market_probs/persist_market_observations permaneceram iguais.

Captura DC fixa: fixture id1000032566887012; decisão11/09/2026 23UTC; kickoff12/09 00UTC; dupla Pinnacle/bet365.bet.br; janela22:58:30..<23:00UTC; helper inicial22:55..22:59:15UTC; uma consulta limitada; reserva20 e marcador anterior à chamada. Leia CONTINUIDADE DC integralmente antes de qualquer ação. Helpers/agenda não foram alterados. Ferramenta view só retornou cartão, statusativo desconhecido; não duplicar automação completar-dados-do-brasileir-o da tarefa01a08756-2962-7c43-9773-c790cc81329d. Não coletar antecipadamente nem reconstruir corte perdido.

Continue trabalho necessário viável. Não afirme conclusão integral, operação homologada ou lucro sem a evidência correspondente. Atualize registros/guias e mantenha backups verificáveis ao integrar.
''',encoding='utf-8')

(docs/'REPRODUZIR.md').write_text('''# Reprodução delimitada

Raiz de trabalho: C:/BRASILEIRAO/brasileirao-predictor. Python isolado: C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe. SDK: .../dotnet-sdk/dotnet.exe. Dependências previamente instaladas e fixadas em RI; não usar o venv mínimo PF da captura para desenvolvimento.

1. Conferir arquivos/hash/base pelo recibo AUDITORIA/CONTINUACAO_INTEGRAL_2026-09-10.json e pelo manifesto. Ler efeitos dos comandos antes de executá-los. Não executar pytest por glob de todo o repositório, pois inclui avaliadores protegidos.
2. O runner work/completion-2026-09-10/run_isolated.py exige nova saída e lista explícita de testes, guardando JUnit e isolation.json. A lista integrada exata está em evidence/integrated-python-03/isolation.json. Sem rede/subprocessos e sem DB fora do diretório sintético.3 casos do init e1 adicional de schema legado em storage-final. Não remover barreiras para fazer testes passarem.
3. tools/runtime_lab/run.py cria apenas seu Redis descartável por PID/run_id em127.0.0.1:26380, DB14/15/13, sem persistência; exige --output novo, --repo, --server, --server-sha256, --dotnet e --nuget-cache. Os argumentos completos estão nos recibos runtime-*/receipt.json. Não substituir endpoint por servidor existente. --cross-only repete apenas a falha entre processos.
4. check_changed.py conserva logs Ruff/Pyright; build_package.py constrói offline wheel/sdist, instala a wheel em destino explícito e executa CLI com entradas sintéticas. Consultar package-receipt-final.json. Nenhuma CLI de coleta/settlement operacional participa desse smoke.
5. Novo decoder: python -m brasileirao_predictor.data.odds_api_snapshot RAW --sha256 SHA --received-at ISO_COM_FUSO --output NOVO_JSON [--event-id ID]. RAW deve ser resposta completa do endpoint correto. Saída inválida retorna2; vazio válido retorna0 com execução ABSTAIN. Arquivo já existente é recusado. Isso não captura odds ou prova execução.
6. Bitemporal mudou identidade da PK. Banco legado não é migrado implicitamente; a leitura abre erro explícito e preserva o original. Uma futura migração deve usar cópia isolada, preservar raw/clocks/charters e demonstrar equivalência antes de qualquer integração permitida.

Banco/Redis operacional, .env, privados e conteúdo de coortes não são inputs desta reprodução. Fonte de documentação pode mudar; os recibos datados preservam o que foi recebido. Artefatos de investigação ficam em work; versões anteriores e falhas não são apagadas.
''',encoding='utf-8')

# Copy only pre-inspected machine evidence, never raw provider pages or private data.
for directory in root.iterdir():
    if directory.is_dir() and directory.name not in {'sources','sources-followup'}:
        for name in ('junit.xml','isolation.json','receipt.json','python-junit.xml'):
            source=directory/name
            if source.is_file():
                target=evidence/directory.name/name;target.parent.mkdir(exist_ok=True)
                shutil.copyfile(source,target)
        if directory.name.startswith('runtime-'):
            for source in directory.glob('dotnet-results/*.trx'):
                target=evidence/directory.name/source.name;target.parent.mkdir(exist_ok=True)
                shutil.copyfile(source,target)
            for source in directory.glob('kernel-startup-*.log'):
                target=evidence/directory.name/source.name;target.parent.mkdir(exist_ok=True)
                shutil.copyfile(source,target)
for name in ('sources','sources-followup'):
    target=evidence/name;target.mkdir(exist_ok=True)
    shutil.copyfile(root/name/'receipts.json',target/'receipts.json')
for name in ('automation-view.json','quality-checks-final.json','ruff-check-final.log','ruff-format-check-final.log','pyright-final.log'):
    if (root/name).exists():shutil.copyfile(root/name,evidence/name)

note='''# Estado vigente — CPL-20260910

Correções verificadas em previsão, temporalidade, preços, contabilidade e infraestrutura.196 testes Python aprovados;27 com Redis real;119 casos.NET aprovados entre execuções separadas, com falha intermitente de inicialização preservada. Prontidão técnica delimitada; dados comerciais insuficientes; lucro executável não demonstrado. Mandato integral ainda em andamento:78 leituras semânticas registradas de450 arquivos inventariados,58 protegidos por contrato.

{links}

Os estados datados anteriores abaixo permanecem como histórico, com seus escopos próprios.

---

'''
guides={
    'docs/ESTADO_ATUAL.md':'[Resultado](continuation/completion_2026-09-10/RESULTADO.md) · [Registros atuais](continuation/completion_2026-09-10/REGISTROS.md).',
    'docs/DATA_MAP.md':'[Mapa de campos/fontes e lacunas](continuation/completion_2026-09-10/MAPA_DADOS.md).',
    'docs/INDICE_DOCUMENTACAO.md':'[Entrega CPL](continuation/completion_2026-09-10/RESULTADO.md) · [Sistema](continuation/completion_2026-09-10/MAPA_SISTEMA.md) · [Reprodução](continuation/completion_2026-09-10/REPRODUZIR.md).',
    'docs/continuation/RETOMADA.md':'[Próximo prompt CPL](completion_2026-09-10/PROXIMO_PROMPT.md) · [Registros](completion_2026-09-10/REGISTROS.json).',
    'HANDOFF.md':'[Resultado CPL](docs/continuation/completion_2026-09-10/RESULTADO.md) · [Continuação](docs/continuation/completion_2026-09-10/PROXIMO_PROMPT.md).',
}
previous=root/'previous-guides';previous.mkdir(exist_ok=True)
for rel,links in guides.items():
    target=repo/rel
    old=target.read_text(encoding='utf-8')
    backup=previous/rel;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copyfile(target,backup)
    if not old.startswith('# Estado vigente — CPL-20260910'):
        target.write_text(note.format(links=links)+old,encoding='utf-8')
readme=repo/'README.md'
if not (previous/'README.md').exists():shutil.copyfile(readme,previous/'README.md')
old=readme.read_text(encoding='utf-8')
if 'Continuação CPL-20260910' not in old:
    marker='Pesquisa quantitativa e software para o Brasileirão Série A, em C:/BRASILEIRAO.\n'
    readme.write_text(old.replace(marker,marker+'\n**Continuação CPL-20260910:** contratos de dados/previsão, contabilidade e .NET corrigidos. A revisão integral permanece em andamento; lucro executável não demonstrado. [Resultado atual](docs/continuation/completion_2026-09-10/RESULTADO.md), [correções/limites](docs/continuation/completion_2026-09-10/REGISTROS.md) e [continuação](docs/continuation/completion_2026-09-10/PROXIMO_PROMPT.md).\n',1),encoding='utf-8')
outside=Path('C:/BRASILEIRAO/LEIA_PRIMEIRO.md')
if not (previous/'LEIA_PRIMEIRO.md').exists():shutil.copyfile(outside,previous/'LEIA_PRIMEIRO.md')
old=outside.read_text(encoding='utf-8')
if not old.startswith('# Estado vigente — CPL-20260910'):
    outside.write_text(note.format(links='[Resultado CPL](brasileirao-predictor/docs/continuation/completion_2026-09-10/RESULTADO.md). Entrega e backups em AUDITORIA/CONTINUACAO_INTEGRAL_2026-09-10.json.')+old,encoding='utf-8')
shutil.copyfile(docs/'PROXIMO_PROMPT.md',Path('C:/BRASILEIRAO/INSTRUCOES/PROXIMO_PROMPT_APOS_CONTINUACAO_INTEGRAL_2026-09-10.md'))
checkpoint=docs/'CHECKPOINT_TRABALHO.md'
old=checkpoint.read_text(encoding='utf-8')
if not old.startswith('> Checkpoint intermediário'):
    checkpoint.write_text('> Checkpoint intermediário preservado. Para o estado posterior desta rodada, consultar REGISTROS.json e RESULTADO.md.\n\n'+old,encoding='utf-8')
print(json.dumps(dict(claims=len(claims),issues=len(issues),coverage=coverage),ensure_ascii=False))
