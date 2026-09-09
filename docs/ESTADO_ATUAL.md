# Estado atual — 09/09/2026, continuação ER-20260909

Referência vigente para a raiz **`C:/BRASILEIRAO`**. O
[mandato](continuation/MANDATO_LUCRO_2026-09-09.md) define objetivo e restrições.
**Dados adicionais obtidos; lucro executável não demonstrado; capital bloqueado.**

Próximo trabalho solicitado: [revisão integral e resolução](continuation/REVISAO_INTEGRAL_2026-09-09.md),
começando pela conferência do existente e das premissas. O handoff foi preparado;
a revisão integral ainda não foi executada. As verificações abaixo mantêm seu escopo original.

## Código e ambiente

Checkout `C:/BRASILEIRAO/brasileirao-predictor`, branch `main`. A base da
continuação ER foi `7f18d543891cb3e68bb82c0a0d9fb58f9a8f12c0`, posterior
à rodada DC e à consolidação dos dados. O SHA final, diff e backup constam do recibo
`C:/BRASILEIRAO/AUDITORIA/EXECUTION_READINESS_2026-09-09.json`.
Nenhum push desta rodada foi realizado. O pacote original permanece associado
a d42a3e0; não houve reset ou recriação de branches antigas.

Python 3.13.12, pytest 8.4.2, Ruff 0.12.12 e Pyright 1.1.405 em
`C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv`.
Core 3.2.0 / Ops 4.1.0 continuam fixados no lock, mas não foram instalados no
ambiente mínimo. Aplicação operacional completa, .NET/Redis/Compose não foram
instalados ou validados por esta rodada. Ferramentas de sistema e o aplicativo
Codex continuam sendo dependências externas à pasta; mover um venv pode exigir
reinstalação. Não confundir código versionado, ambiente instalado e serviço ativo.

## Dados e integridade

A migração foi conferida por SHA-256 e CRC: **12.423 entradas mais o manifesto**,
9.477.623.208 bytes descompactados, em `C:/BRASILEIRAO/DADOS_PRESERVADOS`.
Recibo original: `C:/BRASILEIRAO/AUDITORIA/verificacao_migracao_2026-09-09.json`.
ZIP, bundle, cinco snapshots SQLite e configurações recebidas foram preservados.
As 21 entregas PF foram copiadas com igualdade de hash para `ENTREGAS`;
o mandato original está em `INSTRUCOES`.

Os novos insumos ficam em `C:/BRASILEIRAO/work/data-completion-2026-09-09`:

| Insumo | Resultado e interpretação |
| --- | --- |
| OddsPapi Jan–Jun/2026 | 177/177 timelines verificadas; 623.271.596 bytes; 22 reutilizadas e 155 novas |
| Football-Data oficial | CSV recuperado; 380 jogos de 2025, 158 pares closing numericamente completos |
| Catálogos atuais | Identidades de bookmaker e 21 fixtures elegíveis; evento escolhido antes das odds |
| Capturas prospectivas iniciais | Três capturas de um evento com recibos reais; coleta Bet365 Brasil sinalizada como inativa nas três |
| Acesso/custo de dados | Plano gratuito existente verificado; contador 62 → 67/250; reserva 20 preservada |

Os 177 arquivos estão completos para o universo declarado. Isso não equivale
à completude dos campos exigidos: faltam procedência temporal histórica,
capacidade, condições reais de custo e validação futura. O
[resultado atual](continuation/data_completion_2026-09-09/RESULTADO.md) e a
[matriz de pendências](continuation/data_completion_2026-09-09/PENDENCIAS.md)
detalham a diferença. Nenhum resultado de 2026 ou de coorte protegida foi usado.

## Operação e continuidade

Nenhum banco operacional, Redis, serviço ou tarefa Windows do projeto foi
iniciado. As coletas pontuais DC foram processos de aquisição independentes,
encerrados após gravar seus recibos. A chave existente de API de dados foi lida
somente por esses processos; os testes e a pesquisa offline ficaram sem credenciais.

Está ativo um acompanhamento **nesta tarefa do Codex**, diário às **19:57 de
São Paulo**, para a captura fixa de 11/09 antes das 20:00. Sua janela, quota,
idempotência e encerramento estão em
[CONTINUIDADE.md](continuation/data_completion_2026-09-09/CONTINUIDADE.md).
A definição ativa reside no armazenamento do aplicativo; uma cópia documental
fica em `C:/BRASILEIRAO/AUDITORIA/automacao_dados_2026-09-09.toml`.
O computador precisa estar ligado e o aplicativo em execução para acessar os
arquivos locais. Agendamento não garante chegada na janela nem disponibilidade da API.

H14/H15/H9/A1, resultados, observadores, contratos, claims e agendas permanecem
intactos. As tarefas exportadas da migração não foram importadas. Não restaurar
bancos por cima de dados ativos nem executar avaliadores para organizar arquivos.

## Evidência e checks

Zero pares admitidos para execução. O replay closing de 2025 congelou 32
escolhas antes dos labels e apurou −9,24u no cenário de fricção 2%, banca 100u.
Todas as seleções ocorreram no período em que a fonte avisa desatualização da
referência Pinnacle; o saldo é aritmético condicional, não validação econômica.

**153 testes passaram**: os 138 da rodada DC mais 15 ensaios novos da rotina
futura. Cinco regressões falharam antes das correções. Ruff e Pyright dos dois
executores alterados passaram. A tipagem dos três módulos puros e a conferência
Fraction anteriores permanecem válidas para o código inalterado. A rotina
corrigida preserva respostas inválidas e produz rejeições rastreáveis. Checks são delimitados à pesquisa,
não evidência de CI remoto atualizado ou instalação operacional completa.

## Correções e condições ER

[Resultado ER](continuation/execution_readiness_2026-09-09/RESULTADO.md): cinco
fontes públicas HTTP 200, sem consulta autenticada ou uso de quota de odds.
O campo bookmakerIsActive descreve principalmente coleta do agregador; false
não prova suspensão na casa. Regras públicas de limite e imposto foram
documentadas sem preencher capacidade, moeda ou custo pessoais desconhecidos.

As duas rotinas corrigidas foram copiadas para seus caminhos ativos em
`C:/BRASILEIRAO/work/data-completion-2026-09-09`; versões anteriores, fontes e
recibos novos estão em `C:/BRASILEIRAO/work/execution-readiness-2026-09-09`.
Fixture, horário, quota e agenda não mudaram. Falha HTTP não autoriza retry;
corpo de captura inválido pode e deve receber auditoria de rejeição.

## Limite da garantia da pasta

Todos os arquivos recebidos no pacote verificado, o Git recuperado e as
entregas e dados conhecidos destas sessões estão sob `C:/BRASILEIRAO`.
A captura de 08/09 não é imagem integral do computador antigo: o manifesto
registra omissão do cache `.pytest_cache` por acesso negado na origem.
Arquivos nunca enviados ou criados depois da captura não podem ser atestados.
Os documentos históricos e contratos congelados são indexados e preservados;
os guias atuais foram reconciliados com a rodada DC.
