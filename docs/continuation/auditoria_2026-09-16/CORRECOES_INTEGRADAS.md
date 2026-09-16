# Correções integradas aos checkouts — 15/09/2026

## O que mudou nesta execução

As correções anteriores deixaram de existir somente em candidatas: os arquivos
foram integrados a `C:/BRASILEIRAO/brasileirao-predictor` e `C:/CAIN/projeto`.
As mudanças que já existiam no CAIN foram preservadas. Backups dos arquivos
substituídos e recibos de hashes estão nos diretórios de QA correspondentes.
Não houve commit, push, merge remoto ou atualização dos ambientes instalados.

### Brasileirão

- Bloqueio de contrato incompatível antes do claim e antes de leitura da coorte.
- Recusa a aprovação com guardrail ausente ou intervalo inválido.
- Tratamento de intervalos malformados, NaN, infinito, booleanos e valores textuais.
- Mensagens deixam explícito que intervalo incluindo zero não demonstra equivalência.
- Resultados com apenas um placar preenchido deixam de ser tratados como jogo completo.
- IDs de evento duplicados no ledger bloqueiam o cálculo, impedindo inflar a amostra.
- Validação de alpha e p-values no componente Holm; família completa obrigatória.
- Componentes puros Brier OU2.5 e Holm integrados ao código, sem autorizar automaticamente
  a avaliação dos protocolos protegidos.

**108 testes passaram** no conjunto dirigido do Brasileirão. Os testes usam apenas
dados sintéticos e preservam a proteção de avaliação única. A falha inicial desta
rodada foi no harness de isolamento ao consultar metadados do Windows; foi corrigida
pré-carregando esses metadados antes da proibição de subprocessos. Logs preservados.

### CAIN: falha semântica reproduzida e tratamento corrigido

Foi iniciado um backend temporário local, porta 11439, com o modelo já existente
`qwen3.5:4b`, digest `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`.
Os testes usaram banco e identidade QA, sem banco pessoal ou dados protegidos.

A primeira tentativa, baseada em reforçar o prompt, não resolveu suficientemente
o problema: a resposta de uma claim alterou a capitalização do estado e chamou
feature de recurso; os demais resultados estão preservados nos recibos individuais.
Essas tentativas não foram apagadas ou contadas como aprovação.

Correção final: tabelas de claims/hipóteses com cabeçalhos explícitos passam por
uma resposta determinística de campos literais. Ela preserva IDs, enunciados,
horizontes, estados, evidências, L/Q e ressalvas existentes, sem traduzir nem
completar termos. Os cabeçalhos e demais contextos são verificados e incluídos
na proveniência. Colunas ambíguas, tabelas sem rótulos e formatos não suportados
não entram silenciosamente nesse caminho. A resposta declara que a transcrição
não valida o experimento nem resolve conflitos entre revisões.

Os casos de uma claim, três claims e ordem invertida foram confirmados como
`literal_claim_table`, todos com zero chamadas ao modelo. Isso corrige a reescrita
indevida nessa classe de fonte; não certifica a semântica de toda resposta livre.
O workflow foi versionado para não misturar essa alteração com execuções antigas.

A renderização existente reconhece `answer_mode=literal_fields`; o workflow aceita
a resposta sem tratá-la como erro de geração. Essa compatibilidade foi inspecionada
no código, sem alegar teste visual da instalação principal.

A suíte dirigida inicial passou 44 testes. Na verificação após integração surgiram
3 falhas de conciliação: versão de prompt esperada antiga e dois casos de preâmbulo
documental presentes nas mudanças concorrentes. A expectativa foi atualizada e a
cópia QA recebeu o `grounding.py` corrente, sem sobrescrever esse arquivo no projeto.
O resultado final está no recibo desta entrega. Avisos de depreciação das
dependências permanecem visíveis; não houve atualização global de dependências.

O backend temporário e seus processos filhos foram encerrados após a verificação.

## O que não pode ser resolvido fabricando dados ou mudando um protocolo

- As duas reconstruções retrospectivas H15 continuam separadas dos originais.
  Quatro previsões por braço daquele recorte continuam sem proveniência suficiente.
  H14 continua sem as probabilidades OU2.5 históricas/baseline necessárias.
- O contrato H14/H15 original exige OU2.5 e decisão familiar, mas não fornece tudo
  que falta para restaurar a evidência original. O bloqueio é intencional; remover
  esse bloqueio não seria uma correção.
- A função Holm implementa o ajuste para p-values válidos; não inventa a definição
  estatística dos p-values nem altera retroativamente o método congelado.
- Os dois relatórios EXP-001, `integrated_xg_v2` e a ligação histórica H11 precisam
  de fontes adicionais para encerrar as lacunas documentais já descritas.

Esses itens continuam registrados como dependências de evidência/protocolo.
Não são apresentados como bugs corrigidos nem como aprovação científica.

## Limites da entrega

Código corrigido, testado no escopo identificado e integrado nos checkouts.
Instalações operacionais, bancos, configurações pessoais, contratos, coortes,
claims de avaliação e agendamentos foram preservados. Não houve avaliação
científica ou nova reconstrução de probabilidades nesta execução.
Não se afirma ausência universal de bugs. Os números de testes e os hashes de
entrega são delimitados pelos arquivos e recibos incluídos no pacote.
