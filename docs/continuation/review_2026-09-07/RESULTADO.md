# Revisão final do projeto — 07/09/2026

**O projeto foi revisado, corrigido e reexecutado. Ainda não temos lucro demonstrado.** O novo replay repetiu o prejuízo de **1,23 unidade**, equivalente a **R$61,50 com R$50 por aposta**, nos 58 jogos disponíveis do segundo turno. As melhorias corrigiram falhas de implementação; não criaram uma vantagem econômica nos dados avaliados.

| Resultado da simulação | Calibrado em 2025 | Mesmo modelo sem calibração |
|---|---:|---:|
| Primeiro turno: apostas | 46 | 153 |
| Primeiro turno: saldo líquido | −14,511 u | +0,710 u |
| Segundo turno disponível: apostas | 9 | 46 |
| Segundo turno: acertos / erros | 4 / 5 | 10 / 36 |
| Segundo turno: saldo líquido | **−1,230 u** | **−19,495 u** |
| Segundo turno: ROI líquido | **−13,67%** | **−42,38%** |
| Segundo turno: saldo a R$50 por aposta | **−R$61,50** | **−R$974,75** |

O custo adicional simulado é de 2% do valor apostado, inclusive nas perdas. Com banca inicial de R$5.000 e aposta fixa de R$50, a versão calibrada terminaria o trecho do segundo turno em R$4.938,50. A maior queda desde um pico seria R$153. Os 190 jogos do turno estão preservados; 132 ainda não têm resultado avaliável neste corte. Não é uma previsão do saldo final do campeonato.

Foram corrigidos cinco pontos concretos:

1. **Mercado errado nas odds de gols.** O parser podia aceitar escanteios/cartões, outro período ou cotações conflitantes como total de gols. Reproduzi os erros e fiz os caminhos de ingestão usar a mesma validação de mercado, período, linha e preço. Sem payload histórico, não inventei uma correção retroativa dos preços.
2. **Subprocessos sobrevivendo ao timeout.** O launcher agora encerra somente a árvore que iniciou. Se não conseguir confirmar a limpeza, registra a falha explicitamente. A regressão usa processos sintéticos e comprovou o encerramento.
3. **Chave exposta em erro de conexão.** Exceções de transporte do EXP001 agora são sanitizadas, inclusive o contexto da traceback, preservando os testes com chaves fictícias.
4. **Comandos apontando para caminhos inexistentes.** Dez referências antigas foram corrigidas; os onze comandos do manifesto resolvem para arquivos existentes. Isso não ativou tarefas desabilitadas.
5. **Falso alarme da barreira de Elo.** H14 captura o serving antes do jogo, mas a barreira o classificava como pesquisa retrospectiva. A exceção passou a reconhecer somente esse caminho exato. Quatro regressões continuam bloqueando pesquisas e cópias novas indevidas. O código e o protocolo H14 não foram alterados.

A documentação também foi atualizada: H14/H15 já estão em coleta passiva. Os heartbeats de ambas confirmaram término com código zero usando o novo launcher. As sete agendas previstas continuam habilitadas. Conclusão do processo não significa coleta completa nem lucro.

| Validação executada | Resultado |
|---|---|
| Suíte geral Python sobre o código final isolado | **1.082 aprovados**, 1 integração Redis não executada |
| Replay e diagnóstico probabilístico | **103 aprovados** |
| Ruff e formatação | Aprovados; **344 arquivos** formatados |
| Tipagem Python | **0 erros e 0 avisos** |
| Barreiras de pesquisa somente leitura / Elo | Aprovadas; 10 módulos e 16 arquivos verificados |
| Compilação .NET 10 | Aprovada, sem erros ou avisos |
| Testes .NET sem Redis | **18 aprovados** |
| Pacote Python wheel | Construído no ambiente isolado |
| Cobertura global instrumentada | **50,59%**, acima do limite existente de 45% |
| Hashes científicos protegidos | **14 preservados** |

A suíte executou em worktree separado, com schema de banco vazio e sem copiar credenciais ou dados operacionais. A rede externa dos processos Python foi bloqueada. A cobertura foi medida na execução de 1.078 testes; a execução final acrescentou quatro regressões da barreira CI. A quantidade de testes e o limite de cobertura não provam ausência de todos os defeitos.

**Integração pendente:** o Docker não respondeu e o Windows negou a abertura do serviço para iniciá-lo. Por isso, não homologuei o teste Python com Redis, os 13 testes .NET WorkerRuntime nem o E2E completo do Compose. O script VALIDAR_REDIS_ISOLADO.ps1 foi preparado e teve sua sintaxe validada para executar os testes Redis quando o Docker estiver disponível. Ele usa um Redis descartável em portas locais exclusivas, sem volumes, e não interrompe serviços existentes. Essa parte permanece não executada.

Reexecutei o treino, a calibração e a simulação do candidato fixado, conferindo **760 previsões e 760 decisões**: probabilidades, seleções e saldos se repetiram. Uma implementação independente conferiu os pagamentos. Também reexecutei as **13.680 decisões das 12 políticas históricas de 2023–2025**, sem mudança nos resultados, e conferi **3.214 relações aritméticas da extensão de 51 jogos**, sem divergências. Não houve nova busca de parâmetros em 2026.

Na qualidade probabilística, comparei as previsões nos mesmos jogos com as odds sem margem e com frequências históricas estimadas apenas em 2021–2024. O modelo bruto teve erro médio maior que o mercado nos seis painéis de mercado/turno. Em 1X2 e total de gols, a calibração deu peso zero ao modelo e apenas reproduziu as odds sem margem. Em ambas marcam, a versão calibrada também teve erro maior que o mercado nos dois turnos. Os intervalos por rodada são descritivos, com poucas rodadas no segundo turno e sem ajuste por múltiplas comparações; não transformam o resultado em garantia sobre o futuro.

Eu manteria a coleta passiva e as correções de integridade. Acrescentei os comparadores simples, a incerteza por rodada, a reprodução dos cálculos e um fingerprint científico que não muda só porque a otimização demorou alguns milissegundos a mais. Retiraria este candidato da fila de promoção para apostas reais: o resultado atual não justifica promovê-lo. Não removi evidências antigas nem alterei retrospectivamente seus planos.

Há três limites essenciais na interpretação. **Primeiro**, Elo e parâmetros ficaram congelados no fim de 2024 por escolha do protocolo; isso não reproduz as atualizações contínuas do serving. Atualizar o Elo agora criaria outro candidato após ver os resultados, sem consertar o teste anterior. **Segundo**, os turnos oficiais se sobrepõem no calendário por adiamentos: a rodada 4 teve Flamengo–Mirassol em 02/09, depois do começo do segundo turno em 25/07. Como o primeiro turno não foi usado para ajustar a regra, isso não muda os pagamentos, mas impede dizer que todo o teste terminou antes do início da simulação. **Terceiro**, as odds retrospectivas não têm comprovação de casa, horário de oferta ou execução pré-jogo. Resultados de placares também não têm um histórico completo de revisões.

A verificação externa foi amostral: uma notícia oficial da CBF confirma Cruzeiro 2–1 Flamengo e Internacional 0–0 Atlético-MG, usados no replay. Isso confirma esses dois placares, não as cotações nem os demais 246 jogos; a tabela detalhada apresentou erro de acesso ao abrir. [Fonte: CBF, balanço da 24ª rodada](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro-serie-a/a/palmeiras-goleia-vasco-e-volta-a-abrir-vantagem-na-lideranca-do-brasileirao).

**Estado final:** código corrigido e verificações locais disponíveis aprovadas; integração ainda pendente; modelo avaliado sem vantagem econômica demonstrada e com prejuízo no segundo turno disponível. Nenhuma aposta real foi colocada. O arquivo estado_final.json registra esse parecer e os hashes; evidencias contém os relatórios e recibos; codigo contém os arquivos alterados e instrumentos da revisão.
