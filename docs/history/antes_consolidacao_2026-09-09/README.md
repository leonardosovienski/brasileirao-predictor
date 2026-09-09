# brasileirao-predictor

Consolidação de 08/09/2026: código local e remoto reunidos, mantendo o runtime
Redis v2 e as dependências fixadas Core 3.2.0 / Ops 4.1.0. O estado e as
validações desta integração estão no primeiro checkpoint de `HANDOFF.md`.
As notas datadas abaixo preservam o histórico das respectivas execuções.

Retomada sem depender do histórico do chat:
[prompt atual](docs/continuation/PROMPT_MELHORIA_LUCRO.md) e
[guia com resultados, caminhos persistentes e pendências](docs/continuation/RETOMADA.md).

> **Revisão final local — 2026-09-07.** Correções de escopo das odds de gols,
> encerramento da árvore de processos no timeout, sanitização de erros de rede
> e caminhos do manifesto foram aplicadas. A suíte final isolada passou com
> 1.082 testes Python; tipos, lint, formatação, wheel e build .NET passaram.
> Integração Docker/Redis ainda não revalidada nesta sessão: o serviço Docker
> não respondeu e o Windows negou a abertura do serviço para iniciá-lo.
>
> A qualidade econômica continua **NÃO DEMONSTRADA / CAPITAL BLOQUEADO**.
> O replay fixo com treino 2021–2024 e calibração 2025 foi reproduzido: no
> segundo turno disponível, 9 apostas e saldo líquido −1,23 unidade em 58
> jogos avaliáveis de 190 oficiais. Odds retrospectivas não comprovam
> execução; o candidato estático não reproduz a atualização contínua do
> serving. O teste de probabilidades também não mostrou vantagem sobre o
> mercado. Veja o checkpoint atual em `HANDOFF.md`.

> **Checkpoint histórico — 2026-09-04.** Coorte prospectiva H14 (serving-v2 vs.
> climatologia) e H15 (refit 10 vs. 100 jogos) começaram a coletar de verdade
> — persistência append-only pré-kickoff rodando, avaliação só em
> `n>=900` (ponto único, gate mecânico). Gate A1 (odds multi-casa) com relógio
> de 7 dias em andamento. Capital continua bloqueado em todos os mercados.
> Veja o checkpoint mais recente em `HANDOFF.md`.

> **Atualização econômica — 2026-09-01.** O candidato residual de totais avalia
> Over e Under com odds realmente observadas, pares temporalmente compatíveis e
> EV/Kelly/P&L líquidos de fricção. A avaliação permanece `SHADOW`, sem promoção
> de hipótese e com capital bloqueado. Veja o checkpoint mais recente em
> `HANDOFF.md`.

> **Estado corrente — 2026-08-26:** a auditoria matemática posterior ao
> relatório consolidado corrigiu o normalizador NB+Dixon–Coles, o domínio de
> `rho`, o decay terminal do Elo, a climatologia prequential e o relatório de
> estratos pequenos. Métricas produzidas antes dessas correções são históricas
> e precisam ser recalculadas antes de qualquer comparação científica. Capital
> continua bloqueado. Veja `docs/AUDITORIA_MATEMATICA_E_CORRECOES_2026-08-26.md`.

Backfill histórico point-in-time é mantido fora de `matches.db`, em raw
imutável, curated SQLite isolado e views de avaliação com clocks de disponibilidade.
Veja `docs/BACKFILL_POINT_IN_TIME.md` e `docs/CLOSING_LINE.md`.

O mapa de armazenamento — banco, tabelas, snapshots A1, quarentena, métricas,
ledgers, volumes e comandos de auditoria — está em [`docs/DATA_MAP.md`](docs/DATA_MAP.md).
O dossiê consolidado sobre acertos, erros, calibração, lambdas, mercados e
causas está em [`docs/DOSSIE_ANALISE_PREDICTOR_2026-08-26.md`](docs/DOSSIE_ANALISE_PREDICTOR_2026-08-26.md).
O fechamento completo, incluindo 2025 aberto, governança, coletor e lacunas,
está em [`docs/RELATORIO_FINAL_CONSOLIDADO_2026-08-26.md`](docs/RELATORIO_FINAL_CONSOLIDADO_2026-08-26.md).

A auditoria adversarial de 2026-09-05, com os sete achados, a evidência
reproduzível de cada um e dois adendos de encerramento, está em
[`docs/AUDITORIA_ADVERSARIAL_2026-09-05.md`](docs/AUDITORIA_ADVERSARIAL_2026-09-05.md).
[`docs/ESTADO_LOCAL_E_OPERACAO.md`](docs/ESTADO_LOCAL_E_OPERACAO.md) registra
o estado local da auditoria de 06/09. Para operar, confira primeiro o checkpoint
mais recente de `HANDOFF.md`; o documento histórico reúne o que NÃO está versionado — onde
vive o `matches.db`, como renovar o atestado de poder (validade de 7 dias, e
todo bump do `predictor-core` o invalida), o estado da coleta agendada no
Windows Task Scheduler, e as diferenças entre ambiente local, CI e sandbox que
já causaram diagnóstico errado.

A coleta prospectiva atual preserva contratos completos e capital bloqueado;
operação e monitoramento: `docs/SHADOW_PROSPECTIVE_RUNBOOK.md`. H3/H5 são
históricas/substituídas; H9 é a replicação econômica inconclusiva; H13 foi
substituída. H14 e H15 têm desenhos pré-registrados e sua coleta passiva foi
retomada em 07/09/2026. Heartbeats operacionais confirmam execução; isso não
equivale a conclusão da coleta, avaliação científica ou lucro.

A calibração operacional do próximo caminho econômico está definida em
[`docs/A1_OU25_PHASE0_RUNBOOK.md`](docs/A1_OU25_PHASE0_RUNBOOK.md): somente
OU2.5, sem labels, sem picks, sem Kelly e sem capital até homologação do A1 e
congelamento prospectivo do orçamento de fricção.

> ## 📌 ESTADO HISTÓRICO (2026-08-24) — supersedido pela nota acima
>
> Serving com ensemble xG desligado bate a climatologia em 2021–2024, mas
> perde do fechamento 1X2 sem vig; não há edge econômico e o capital permanece
> bloqueado. H12 é a única trial comprovada e H13 é a única pré-registrada
> aberta. TRACK A02 (primeira formulação) e MARKET-02 1X2 deram NO-GO em
> 2026-08-22. A contagem de testes é dinâmica; consulte o CI da `main` em vez
> de copiar um número histórico. Detalhes e pendências operacionais estão no primeiro checkpoint de
> `HANDOFF.md`.

Sistema CLI em Python para previsão e apostas de valor no Brasileirão Série A,
rodando 100% local (Python + SQLite). Fonte única de dados: **Sofascore**
(resultados, placar de intervalo, odds de abertura/fechamento, estatísticas,
xG) — ut_id 325, temporadas 2021–2026. Não existe CSV público equivalente
ao martj42 para clubes: a tabela `matches` (Elo + calibração) é alimentada pelo
espelho `brasileirao_scripts/sync_matches_from_sofascore.py`.

## O que muda em relação ao wc-predictor-v2

| Aspecto | Copa (wc-predictor-v2) | Brasileirão (este repo) |
|---|---|---|
| Times | seleções (martj42 CSV, ~49k jogos) | 20 clubes da Série A (Sofascore) |
| `matches` | ingest.py (CSV remoto) | espelho do Sofascore (**não rode** `python -m brasileirao_predictor.ingest`) |
| Mando | quase tudo neutro | mando real em TODO jogo (`neutral=0`) |
| Identidade | constantes "World Cup" no código | `config.yaml: league / tournament_name` |
| Backtest | params frozen, 1 janela | **walk-forward** por blocos de rodadas (`brasileirao_scripts/backtest_walkforward.py`) |
| Governança | TrialRegistry não consumido | harness + pré-registro obrigatórios (`brasileirao_scripts/governanca.py`) |
| Simulador | bracket Monte Carlo da Copa | **não se aplica** a pontos corridos (encerra com aviso) |
| Telemetria | domínio `wc` | domínio `brasileirao` |

O motor estatístico é o MESMO (genérico por construção): Elo com decay +
Binomial Negativa + Dixon-Coles, calibrado por MLE só com jogos do domínio.
Parâmetros recalibrados com dados do Brasileirão a cada bloco do walk-forward
e pelo `cron_update_models` no serving.

## Pipeline

```
ingest_sofascore.py  →  sofascore_matches (+odds abertura/fechamento, HT, stats, xG)
        │
        └→ brasileirao_scripts/sync_matches_from_sofascore.py → matches (Elo + calibração)
                │
                └→ cron_update_models.py → current_elo + model_parameters (cache serving)
                        │
        ┌───────────────┴────────────────┐
   predict.py / prever.py           brasileirao_scripts/backtest_walkforward.py
   (serving, log obrigatório)       (pesquisa, read-only, GO/NO-GO)
        │
   brasileirao_scripts/odds_shop.py (The Odds API, line shopping pré-rodada)
        │
   bet_log (banca real)  →  settle (aferição pós-jogo)
```

## Uso

```bash
uv sync --all-extras --locked

# Coleta (na máquina do operador; o Sofascore não responde ao sandbox)
python -m brasileirao_predictor.ingest_sofascore                      # 2024 + 2025 + fixtures 2026
python -m brasileirao_scripts.sync_matches_from_sofascore       # espelha p/ matches
python -m brasileirao_predictor.cron_update_models                    # Elo + params de serving

# Governança (ordem obrigatória, uma vez por ciclo de pesquisa)
python -m brasileirao_scripts.governanca                        # harness + pré-registro H1/H2
python -m brasileirao_scripts.backtest_walkforward              # veredito GO/NO-GO

# Previsão
python -m brasileirao_predictor.predict Flamengo Palmeiras            # mando do 1º time é o default do domínio
python -m brasileirao_scripts.prever Flamengo Palmeiras --mando # pacote completo
python -m brasileirao_scripts.prever Flamengo Palmeiras --primeiro-tempo

# Operação (só após GO)
python -m brasileirao_scripts.odds_shop --from-file snapshot.json
python -m brasileirao_predictor.bet_log banca|list|settle|summary

# Testes
python -m pytest            # suíte Python atual; contagem canônica no HANDOFF
python -m brasileirao_scripts.ci_check  # 5 barreiras

# Backup operacional consistente (destino deve ser uma raiz nova)
python -m brasileirao_predictor.backup_restore create --output C:\backups\brasileirao-AAAA-MM-DD
python -m brasileirao_predictor.backup_restore verify --backup C:\backups\brasileirao-AAAA-MM-DD
python -m brasileirao_predictor.backup_restore restore --backup C:\backups\brasileirao-AAAA-MM-DD --destination C:\restore-novo
```

Registros prospectivos novos incluem timestamps exatos de previsão e kickoff,
turno, fonte, preço capturado e fechamento bruto. Registros anteriores
permanecem legados; não são completados retrospectivamente.

## Trials e pré-registro (`data/trials.json`)

O ledger é dinâmico. Não manter contagem ou lista duplicada aqui: nomes,
status, parâmetros, períodos e notas canônicas vivem em `data/trials.json`; o
resumo interpretativo atual fica no primeiro checkpoint de `HANDOFF.md`.

Criar tentativa NOVA exige o atestado do harness de controle positivo
(`data/trials.harness_attestation.json`) — o funil precisa provar que detecta
edge sintético (ataque ×1,3) e rejeita ruído antes de qualquer veredito valer.

## Regras inegociáveis (herdadas da auditoria da Copa)

1. **1X2 sem capital** enquanto não houver edge prospectivo comprovado; o
   mercado 1X2 é baseline obrigatório, não autorização para apostar.
2. Aposta real só em mercado com CLV comprovado no backtest **deste domínio**.
3. Todo palpite entra no log append-only ANTES do jogo (predictions.jsonl);
   todo resultado é aferido (settle) — sem esquecimento seletivo.
4. Pesquisa abre o banco read-only (barreira P12 do ci_check).
5. Elo corrente (`current_elo`) só no serving; pesquisa usa `ratings_asof`.

## Estrutura

```
config.yaml               # league, tournament_name, elo, model, backtest, sofascore
brasileirao_predictor/                      # motor (db, ratings, model, backtest, predict, display…)
brasileirao_scripts/
  sync_matches_from_sofascore.py   # espelho sofascore → matches (novo)
  governanca.py                    # harness + TrialRegistry (novo)
  backtest_walkforward.py          # walk-forward por rodadas (novo)
  prever.py, odds_shop.py, ci_check.py, …
data/                     # matches.db, livros jsonl, trials.json (fora do git)
tests/                    # suíte Python; .NET LineupWorker tem suíte própria
```

Histórico da Copa preservado em `data/results_wc2026_historico.jsonl` e no
repositório original `wc-predictor-v2` (intocado).
