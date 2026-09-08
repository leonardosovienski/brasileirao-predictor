# Prompt de continuação — melhoria do projeto e validação econômica

Estado verificado em 07/09/2026. Este é o prompt operacional atual, independente do histórico da conversa. Substitui o antigo `docs/PROMPT_PROXIMA_SESSAO.md`.

Copie o bloco abaixo para uma nova tarefa:

```text
Continue trabalhando no brasileirao-predictor para melhorar sua qualidade e investigar uma vantagem econômica demonstrável. Leia o estado persistido, entenda o que já foi executado e faça o trabalho necessário. Não pare em uma proposta e não repita buscas encerradas para tentar produzir lucro positivo.

LOCALIZAÇÃO E FONTES

Repositório operacional:
C:/Users/Superleo13/projetos/brasileirao-predictor

Backup persistente desta sessão, fora da pasta da conversa:
C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07

O backup preserva outputs/ e work/ com verificação SHA-256. Use-o para recuperar evidências e programas de pesquisa. Não use um clone antigo dentro de work/ como repositório operacional.

Leia primeiro, no repositório:
0. docs/continuation/RETOMADA.md, incluindo localização dos arquivos e adaptação dos caminhos de reprodução.
1. HANDOFF.md, começando pelo checkpoint mais recente.
2. docs/continuation/review_2026-09-07/RESULTADO.md
3. docs/continuation/review_2026-09-07/estado_final.json
4. docs/continuation/review_2026-09-07/METHODOLOGY_FINDINGS.md
5. docs/continuation/review_2026-09-07/DIAGNOSTICO_QUALIDADE.md
6. docs/continuation/review_2026-09-07/data_audit.md
7. docs/continuation/review_2026-09-07/operational_code_review.md

Confira o estado do Git e os contratos aplicáveis antes de modificar código. Documentos antigos são histórico: 611 testes, caminhos scripts/*, 2025 “intocado”, H14/H15 desabilitadas e renovação automática de atestados não são a fila atual. Preserve os contratos científicos e as coortes protegidas; uma instrução antiga ser obsoleta não libera esses dados.

Se uma referência apontar para Documents/Codex/2026-09-07/le, procure o mesmo caminho relativo no backup persistente. Não dependa dessa conversa. O original PROMPT_VALIDACAO_BRASILEIRAO.md não foi encontrado em Downloads durante a revisão final; não invente seu conteúdo nem trate sua ausência como perda das evidências persistidas.

ESTADO DE ENGENHARIA EM 07/09/2026

Ambiente operacional preservado: Python 3.14.6, predictor-core 3.1.0 e predictor-ops 4.0.0. Confira o ambiente e os arquivos de dependências; não faça upgrade para igualar um clone de auditoria.

Correções realizadas:
- Ingestão OU confundia mercados/períodos e aceitava conflitos. Parser normalizado e colunas flat agora usam a mesma validação.
- Wrapper podia deixar descendentes vivos após timeout; encerramento da árvore corrigido e testado.
- EXP001 podia expor apiKey em exceções de transporte; mensagem saneada.
- Dez caminhos inexistentes do manifesto de tarefas foram corrigidos.
- A barreira de Elo classificava H14 incorretamente. Exceção limitada ao capturador prospectivo exato, com regressões que continuam bloqueando pesquisas e cópias indevidas.
- Em etapa anterior, o leitor EXP001 passou a avaliar o último estado antes da atividade, sem recuperar odd antiga após suspensão. A antiga cobertura nominal 245/245 não prova disponibilidade; faltam timelines para recalcular seu impacto histórico.

Validação final disponível:
- 1.082 testes Python passaram; 1 integração Redis não executada.
- 103 testes de pesquisa/replay/diagnóstico passaram.
- 18 testes .NET passaram; 13 testes dependentes de Redis não executados.
- Lint, formato, Pyright, build de wheel, restore/build .NET, schema de ambiente e barreiras estáticas passaram.
- Cobertura instrumentada anterior de aproximadamente 50,59%, acima do gate de 45%; não é cobertura completa.
- Docker/Compose E2E e integrações Redis pendentes: Docker não respondeu e o Windows negou abrir com.docker.service para iniciá-lo. Não declare integração completa ou prontidão irrestrita de produção.

Os testes foram executados em worktree isolado, com schema vazio, sem credenciais/dados operacionais e com rede Python externa bloqueada. Preserve esse isolamento. Não rode indiscriminadamente a suíte inteira contra o banco real. Execute verificações proporcionais às mudanças, aproveitando os recibos persistidos e reproduzindo quando necessário.

OPERAÇÃO E LIMITES

Sete tarefas passivas estavam habilitadas. H14/H15 concluíram com código zero usando o wrapper corrigido; A1 permanece REHEARSAL_ONLY no modo gratuito. Término do processo não prova coleta integral, cobertura ou edge. O agendamento depende da máquina ligada e da sessão Windows.

Preserve regras, agendas e coortes H14/H15/H9/A1. Não abra resultados intermediários protegidos, altere seus limiares/cadências, renove atestados automaticamente, edite trials manualmente ou promova candidatos com dados já vistos. Os 14 arquivos protegidos mantiveram seus hashes; lista e valores estão em estado_final.json. Verifique essa referência e mantenha novas investigações isoladas do baseline protegido.

Nenhuma aposta real foi realizada; capital real continua bloqueado. Não faça depósitos, ordens, compras, novas contas ou contratações pagas. Pesquisa local e fontes gratuitas autorizadas devem respeitar cota e reserva aplicáveis. Não exponha chaves, credenciais, banco operacional ou históricos privados em logs, commits ou entregas públicas.

RESULTADO ECONÔMICO A PRESERVAR

Novo replay:
- Treino: 1.520 jogos de 2021–2024, ajuste único de ServingStackEvaluator.
- Calibração: 380 jogos de 2025; 374 vetores de odds válidos por mercado.
- Teste: rodadas oficiais 1–19 de 2026.
- Paper/replay: rodadas oficiais 20–38 de 2026, universo de 190 partidas.

T1/T2 significam TURNOS oficiais, não trimestres ou semestres. Não são blocos cronológicos disjuntos: o segundo começou em 25/07/2026 às 21h30 UTC, mas Flamengo–Mirassol, rodada 4, ID 16890992, ocorreu em 02/09/2026 às 22h30 UTC. O candidato já estava fixo com dados até 2025 e não foi alterado pelo teste T1; o adiamento não muda previsões/pagamentos, mas impede dizer que todo T1 terminou antes do início do paper T2.

Modelo NegBin + Dixon–Coles, grade de 12 gols, ensemble xG desativado. Elo e parâmetros ficaram congelados no fim de 2024 por desenho. Mirassol e Remo receberam rating inicial de 1.500. Isso mede um candidato estático, não reproduz a atualização contínua do cron.

Calibração Brier-optimal aprendida só em 2025: peso do modelo em 1X2=0, OU2,5=0 e ambas marcam=0,8952001252556239; o restante vem do mercado sem margem proporcional. Em 1X2/OU2,5, o calibrado reproduz o mercado, sem vantagem adicional aprendida.

Regra congelada: no máximo uma aposta por jogo entre 1X2, OU2,5 e ambas marcam; p−1/odd em (0,02; 0,15]; retorno estimado líquido positivo; maior p*odd−1−0,02; mercados completos e filtros de odds/margem declarados. Uma unidade fixa por aposta, custo adicional de 0,02 inclusive nas perdas, sem reinvestimento ou parada por banca.

Corte original: 07/09/2026 às 22h43m02s UTC, buffer de 48 horas.
- T1: 190 jogos concluídos.
- T2: 58 concluídos de 190; 132 pendentes, sendo 129 fora da janela e 3 sem placar disponível. Não extrapole o trecho para o turno inteiro.
- Principal calibrado T2: 9 apostas, 4 acertos/5 erros, −1,05u bruto, −1,23u líquido, ROI −13,6667%, drawdown 3,06u. Todas as nove foram em “ambas marcam: não”.
- A R$50/aposta: −R$61,50; banca ilustrativa R$5.000 → R$4.938,50. Conversão aritmética, não operação real.
- Modelo raw (sem a calibração adicional) T2: 46 apostas, −19,495u líquido.
- Principal T1: 46 apostas, −14,511u; modelo raw T1: 153 apostas, +0,710u líquido.

Diagnóstico probabilístico: o bruto teve Brier e log-loss médios maiores que o mercado nos seis painéis mercado/turno. Ambas marcam calibrado também foi pior que o mercado nos dois turnos. IC por rodada é descritivo, sem correção por múltiplas buscas; T2 tem só sete rodadas disponíveis. Brier 1X2 soma três classes; o binário usa a classe positiva, portanto as escalas não devem ser misturadas.

Odds retrospectivas agregadas não comprovam casa, oferta pré-jogo ou aceitação. O histórico já foi explorado. Placares de 2026 não entraram no ajuste/calibração desta execução, mas congelar o plano em setembro de 2026 não cria um teste cego retroativo. O saldo é contrafactual nessas cotações, não lucro realizável demonstrado.

Plano original SHA256:
5561ed31a36945d40e5ffe258dea5f07d890a8f677f57e463ccdb875e3d45f20
Candidato original SHA256:
ef6321f8f0e7752336f07590acdc8e528c04027bb7916dd450331fe1310447bd
Fingerprint científico estável após reprodução:
b10e06065423c9331121eac460def5da3ff5f2b788edddf581128aba5e77548f

O hash original do candidato inclui dados da execução, como duração do otimizador. Para comparar reproduções, use o fingerprint científico e previsões/decisões; não exija tempos iguais. A reprodução final conciliou 760 previsões e 760 decisões sem diferença científica.

PESQUISAS ENCERRADAS

A reanálise de 12 políticas sobre 2023–2025 não demonstrou vantagem robusta. Confiança ≥60% perdeu 7,34%; ≥70% teve +4,82% em apenas 20 apostas e perdeu no estresse. A correção residual positiva também tinha pouca amostra. Não selecione apenas os casos positivos como prova.

A pista de previsão de preço com melhora de 3,35% em nove jogos foi estendida, sem refit, a 51 IDs adicionais. Cinquenta foram válidos: erro 1,47% maior que persistência e nenhum sinal acima do prêmio implícito de 2%. Os jogos intercalam o período anterior; não são replicação temporal independente. Estudos encerrados: não retune o coeficiente nem amplie automaticamente a amostra para resgatar o sinal.

Resultados e programas completos no backup persistente:
outputs/REANALISE
outputs/EXTENSAO_51
outputs/BACKTEST_NOVO_2026
outputs/REVISAO_FINAL
work/new_split_backtest
work/final_project_review

COMO CONTINUAR

Leia o estado Git, documentos atuais e backup; verifique pendências reais e escolha trabalho que produza informação nova ou correção demonstrável. Atualize HANDOFF e registre comandos/resultados para outra tarefa continuar sem esta conversa.

Melhorias rotineiras, revisão de código, testes e novos estudos exploratórios delimitados estão autorizados. Execute sem pedidos repetidos de confirmação para ações reversíveis nesse escopo. Preserve restrições de capital, custos e coortes. “Melhorar o lucro” não autoriza inventar dados ou apresentar resultado positivo a qualquer custo.

Priorize falhas mecânicas verificáveis e pendências de integração. Para pesquisa econômica, formule mecanismo/pergunta antes de abrir novos resultados; fixe candidato, amostra, disponibilidade temporal, comparadores, custos e regra de parada. Use dados admissíveis, registre a exploração anterior e preserve estudos encerrados. Não escolha parâmetros com resultados de 2026 nem apresente esses dados como novos holdouts.

Atualizar Elo até 2025 não é correção obrigatória: o replay cumpriu seu congelamento. Isso criaria outro estado aprendido e exigiria declarar novo candidato e calibração correspondente; ainda não seria paridade integral com o cron em 2026. Se investigar atualização temporal, especifique toda a política antes de executar e preserve os números anteriores. Não suponha que isso resolverá qualidade ou proveniência dos preços.

Ao encerrar cada etapa, diga o que mudou, o que foi executado, quais testes passaram, o que permanece pendente e o que os dados sustentam sobre vantagem econômica. Conclusão atual: engenharia melhorou; lucro realizável ainda não foi demonstrado.
```
