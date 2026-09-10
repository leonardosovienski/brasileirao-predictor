# Estado real da arquitetura RCA

O detalhamento histórico de entradas/saídas/caminhos está no [mapa CLO](../closeout_2026-09-10/MAPA_SISTEMA.md); suas contagens e pendências datadas são substituídas pelo registro RCA. O caminho efetivo é CLI/Python, dependências Core/Ops, armazenamento legado, pesquisa isolada e laboratório Python/Redis/.NET. Não foi encontrado frontend web no inventário de fontes.

| Caminho | Estado e decisão | Impedimento restante |
| --- | --- | --- |
| Coleta/DB/Elo/xG/cache compartilhados → predict/display | Legado diagnóstico; correções CPL de consumo preservadas | RI-P11/CPL-P22: cache por contagem, associação aproximada e relógios/artefatos aprendidos não certificam PIT. Dependências protegidas impedem alteração indiscriminada. |
| Raw com recibo → decoder/anchor/PIT → abstenção | Consumidores puros têm validações sintéticas; manter | Preço decodificado não certifica disponibilidade comercial; curated/1 perde status/linha/período/revisões. RCA-P06. |
| Arquivo de escalações → residual_features | Parcial; manter fora da admissão completa | Sem envelope vazio/tombstone, corrupção ignorada e concorrência sem contrato. RCA-P07. |
| Artefato residual → probabilidade/intervalo → decisão shadow | Integridade numérica ARI corrigida; preservar | Hessiana condicional, procedência e incerteza econômica não autenticadas. |
| Gates A10/residual | Corrigir: contratos v2, 49 testes sintéticos finais | Não promovem serving/capital; PSR/DSR e universo recebido não autenticados. RCA-P02/03/04. |
| residual_walkforward → métricas | Exploratório; retirar da interpretação de carteira real | Stake da decisão não aplicada à banca; entrada/labels e clocks não integralmente validados. RCA-P05. |
| BE → oferta hipotética → reserva/conta/resultado | Experimento congelado; conservar | Máximos anônimos não formam prova de ofertas simultâneas executáveis. CPL-P26. |
| Livro manual → liquidação/banca | LGC corrigiu bloqueio de escritores e snapshot de bets; bruto/manual | Coordenação entre arquivos, unidade, moeda, custos e fatos comerciais limitados. RCA-P10. |
| Worker → Redis Functions → kernel → sinal | Protocolo exercitado em laboratório; operação comercial parcial | Elo 1500/1500, posições UNKNOWN, VORP/demo; fornecedor WebSocket não implementado. CPL-P23. |
| MarketOddsCache → MarketStateEngine | Demo não homologada; não iniciar feed genérico | URL example.com no C#, exchange.invalid no Compose; recibo local não é clock comercial; limite total de fragmentos ausente. CPL-P23. |
| LatencyAuditService → percentis/T4 | Retenção e CAS T4 testados anteriormente | SET de RecordAsync não recusa T3 anterior; RCA-P08. |
| Runtime/CI/pacote | Python/SDK/Redis portátil utilizáveis em laboratório; pacote offline passa | Docker/Compose e CI desta revisão não executados. Python 3.14 não reensaiado aqui; tipagem global exclui research. RCA-P09. |
| Backup → restauração Git | ZIP/bundle/hashes conferidos; restore Git separado | Não recupera automaticamente operação nem arquivos nunca recebidos. RCA-P11. |
| H14/H15/H9/A1 e agenda DC | Preservar contratos e estados | Sem avaliação, renovação, consulta de resultados ou mudança de janela. Atividade da agenda não comprovada. CPL-P24. |

Os 283 arquivos classificados como estáticos/pontuais não foram transformados em semanticamente revisados por repetir hashes. Correção de módulos centrais não aprova todos os consumidores. Implementar outro feed ou modificar a coleta compartilhada exige definir o contrato e o efeito nas fronteiras antes, sem inventar credenciais ou disponibilidades. Nenhuma implantação realizada.
