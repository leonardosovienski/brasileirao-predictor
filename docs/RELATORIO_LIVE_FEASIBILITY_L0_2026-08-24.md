# Relatório — Live Feasibility L0 (2026-08-24)

## Resultado

Veredito: **`HOLD_NO_LIVE_VIABILITY_GO`**. A pesquisa documental não autoriza
motor live, treino, backtest, compra de feed ou uso de capital.

| Pergunta do Gate L0 | Resposta |
| --- | --- |
| Eventos históricos timestamped completos por pelo menos duas temporadas da Série A? | **NÃO comprovado** |
| Odds live históricas com granularidade e coverage adequadas? | **NÃO comprovado** |
| Custo total dentro do teto pessoal de USD 600/ano? | **NÃO** |
| Suspensão, reabertura e delay simuláveis? | **SIM, somente Betfair Exchange** |

A evidência, URLs oficiais, preços públicos, formatos e limitações estão
congelados em `docs/experiments/LIVE_FEASIBILITY_01.md`.

## Pendências resolvidas

- o handoff deixou de hardcodar a quantidade de trials e agora fornece o
  comando que deriva a contagem do ledger;
- a ausência de `data/matches.db` em checkout Git limpo foi documentada como
  condição ambiental permanente, com bootstrap e smoke reproduzíveis;
- o gap de venue de Internacional/Bahia ganhou proposta de schema, linhagem
  PIT e proibição de inferência em `docs/COVERAGE.md`;
- a possível lentidão do Elo/força escalar foi registrada como observação
  informativa, sem promover hipótese nem autorizar sweep;
- o registro lógico consolidou o encerramento pré-jogo, o HOLD live e o pivô
  para Motor A / Gate A1.

## Próxima ação única

Fazer PoC gratuita/de catálogo para provar que uma temporada da Série A no
Betfair Historical Data contém `MATCH_ODDS`, `OVER_UNDER_25`, `inPlay`, `pt`,
`status` e `betDelay`. Se essa comprovação exigir compra, não gastar e seguir
diretamente para o coletor Pinnacle×soft do Gate A1.

## Desvios do protocolo

Nenhum. Não houve treino, alteração de serving, coleta paga, leitura de
resultado para selecionar modelo, commit ou push.

## Validação técnica

- `data/trials.json`: JSON válido, 25 nomes únicos, todos com status;
- pytest: 735 passed, 1 deselected, 3 warnings numéricos conhecidos;
- Ruff: verde;
- Pyright: 0 erros, 0 warnings;
- `brasileirao_scripts/ci_check.py`: cinco barreiras verdes, incluindo smokes pré-jogo e
  live com o banco operacional presente;
- `git diff --check`: verde.
