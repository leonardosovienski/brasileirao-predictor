# Relatório final — Roadmap v2

Data: 2026-08-24.

## Resumo executivo

O changeset fecha a implementação segura da Fase 0B e entrega scaffolds PIT e
prospectivo. A execução científica da 0B e o motor live continuam bloqueados
pelos respectivos gates. Capital permanece fora do código.

## Fases completas

### Fase 0 — edge 1X2

Permanece concluída com `NO_GO_CURRENT_RESIDUAL`, conforme MARKET-03. Nenhum
threshold foi reaberto e 2025/2026 não foram usados para resgatar a hipótese.

### Implementação da Fase 0B

O protocolo e o runner MARKET-04 estão completos:

- pré-checagem em 2021–2023 com std, variância, mínimo, máximo, range, P10/P90
  e histograma de largura 5pp para `p_over25` e `p_btts`;
- gate global: qualquer std abaixo de 0,02 produz `NO_GO_STRUCTURAL` e impede o
  carregamento de 2024;
- coverage mínimo de odds completas de 80% para ambos os mercados;
- protocolo condicional de dois lados por mercado, cinco faixas de divergência,
  de-vig, monotonicidade, 1.000 permutações estratificadas e power analysis;
- validação única em 2024 somente depois de todos os gates do dev.

Implementação completa não significa resultado científico: a execução está
bloqueada pela ausência da base operacional.

## Fases em scaffold

### Arquitetura PIT

Foram criados contratos para:

- desfalques;
- escalações;
- xG isolado, em linhagem nova e incompatível com o ensemble H12;
- mando por equipe com shrinkage hierárquico.

Todos exigem mecanismo ex ante, fonte, identificador da fonte, relógios UTC e
disponibilidade estritamente anterior ao kickoff. Treino exige GO externo e
referência imutável. Não existem estimadores, fitting ou integração com serving.

### Validação prospectiva

Foi criado pipeline de paper-trading com ledger append-only, stake flat 1u,
odd capturada e closing pré-kickoff. O avaliador calcula CLV logarítmico, ROI
com IC95 bootstrap, calibração, coverage, PSR, DSR e power pela odd média.

DSR `>=0,95` pode produzir apenas `CAPITAL_GATE: ELIGIBLE_FOR_REVIEW`. A outra
saída é `CAPITAL_GATE: LOCKED`. Não existe saída de liberação automática.

## Fases bloqueadas por gate

### Execução da Fase 0B

Bloqueio: `data/matches.db` operacional ausente. A única cópia encontrada tinha
48 partidas e zero linhas SofaScore/odds, sendo inelegível. Sem ela não é
possível reportar os valores reais de variância, histograma ou coverage.

### Motor live

Estado: `HOLD_NO_LIVE_VIABILITY_GO`. Não foi demonstrada disponibilidade de
feed histórico de eventos e odds timestamped, margem real, suspensões, delay
de aceitação e custo compatível. Somente um placeholder documental foi criado.

### Treino PIT

Bloqueado até Fase 0B ou viabilidade live produzir GO. O gate é executável e
falha sem referência imutável da evidência.

## Hipóteses e governança

`data/trials.json` contém 22 nomes únicos e todos têm status. Foram registrados:

- MARKET-04 OU2.5/BTTS: `pre-registrada`;
- quatro mecanismos PIT: `pre-registrada`;
- viabilidade/motor live: `inconclusiva`, em HOLD;
- scaffold prospectivo: `informativa`.

Os registros sem resultado têm `sharpe=null` e não são apresentados como
evidência confirmatória.

## Validação técnica

- suíte ampla: 721 passed, 1 deselected;
- warnings: três warnings numéricos conhecidos de `rho` no limite em testes;
- Ruff: verde;
- Pyright global: 0 erros, 0 warnings;
- Pyright explícito de `brasileirao_predictor/research/market_0b_resolution.py`, `pit_features/`
  e `prospective_validation/`: 0 erros, 0 warnings;
- CI estático: todas as barreiras verdes;
- smokes de serving e live: pulados porque `data/matches.db` está ausente.

## Desvios explícitos do pedido

1. A Fase 0B foi implementada, mas não executada: faltou a base operacional.
2. A meta de CI foi atendida para suíte, lint, tipos e barreiras estáticas; os
   dois smokes dependentes do banco não puderam rodar.
3. A suíte precisou de bootstrap local do namespace `scripts` porque este host
   possui um pacote externo homônimo que sombreia a pasta do repositório. Isso
   altera apenas a invocação de teste, não o código do projeto.
4. O Pyright global inicialmente encontrou uma incompatibilidade preexistente
   entre o alias configurável `chrome146` e stubs antigos do `curl-cffi`; a
   fronteira recebeu `cast(Any, ...)`, sem mudança de runtime, e ficou verde.
5. Nenhum commit ou push foi feito. Nenhum pedido desta sequência autorizou
   publicação remota explícita.
