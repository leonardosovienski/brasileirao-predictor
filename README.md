# brasileirao-predictor

Backfill histórico point-in-time é mantido fora de `matches.db`, em raw
imutável, curated SQLite isolado e views de avaliação com clocks de disponibilidade.
Veja `docs/BACKFILL_POINT_IN_TIME.md` e `docs/CLOSING_LINE.md`.

A coleta prospectiva atual preserva contratos completos e capital bloqueado;
operação e monitoramento: `docs/SHADOW_PROSPECTIVE_RUNBOOK.md`. H3/H5 são
históricas/substituídas; H9 é a replicação econômica inconclusiva e H13 é a
coorte preditiva pré-registrada vigente.

> ## 📌 ESTADO ATUAL (2026-08-22) — fonte da verdade: HANDOFF.md
>
> Serving com ensemble xG desligado bate a climatologia em 2021–2024, mas
> perde do fechamento 1X2 sem vig; não há edge econômico e o capital permanece
> bloqueado. H12 é a única trial comprovada e H13 é a única pré-registrada
> aberta. TRACK A02 (primeira formulação) e MARKET-02 1X2 deram NO-GO em
> 2026-08-22. Suíte local atual: **637 testes passados**, 1 deselecionado,
> CI 5/5. Detalhes e pendências operacionais estão no primeiro checkpoint de
> `HANDOFF.md`.

Sistema CLI em Python para previsão e apostas de valor no Brasileirão Série A,
rodando 100% local (Python + SQLite). Fonte única de dados: **Sofascore**
(resultados, placar de intervalo, odds de abertura/fechamento, estatísticas,
xG) — ut_id 325, temporadas 2021–2026. Não existe CSV público equivalente
ao martj42 para clubes: a tabela `matches` (Elo + calibração) é alimentada pelo
espelho `scripts/sync_matches_from_sofascore.py`.

## O que muda em relação ao wc-predictor-v2

| Aspecto | Copa (wc-predictor-v2) | Brasileirão (este repo) |
|---|---|---|
| Times | seleções (martj42 CSV, ~49k jogos) | 20 clubes da Série A (Sofascore) |
| `matches` | ingest.py (CSV remoto) | espelho do Sofascore (**não rode** `python -m src.ingest`) |
| Mando | quase tudo neutro | mando real em TODO jogo (`neutral=0`) |
| Identidade | constantes "World Cup" no código | `config.yaml: league / tournament_name` |
| Backtest | params frozen, 1 janela | **walk-forward** por blocos de rodadas (`scripts/backtest_walkforward.py`) |
| Governança | TrialRegistry não consumido | harness + pré-registro obrigatórios (`scripts/governanca.py`) |
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
        └→ scripts/sync_matches_from_sofascore.py → matches (Elo + calibração)
                │
                └→ cron_update_models.py → current_elo + model_parameters (cache serving)
                        │
        ┌───────────────┴────────────────┐
   predict.py / prever.py           scripts/backtest_walkforward.py
   (serving, log obrigatório)       (pesquisa, read-only, GO/NO-GO)
        │
   scripts/odds_shop.py (The Odds API, line shopping pré-rodada)
        │
   bet_log (banca real)  →  settle (aferição pós-jogo)
```

## Uso

```bash
pip install -r requirements.txt

# Coleta (na máquina do operador; o Sofascore não responde ao sandbox)
python -m src.ingest_sofascore                      # 2024 + 2025 + fixtures 2026
python scripts/sync_matches_from_sofascore.py       # espelha p/ matches
python -m src.cron_update_models                    # Elo + params de serving

# Governança (ordem obrigatória, uma vez por ciclo de pesquisa)
python scripts/governanca.py                        # harness + pré-registro H1/H2
python scripts/backtest_walkforward.py              # veredito GO/NO-GO

# Previsão
python -m src.predict Flamengo Palmeiras            # mando do 1º time é o default do domínio
python scripts/prever.py Flamengo Palmeiras --mando # pacote completo
python scripts/prever.py Flamengo Palmeiras --primeiro-tempo

# Operação (só após GO)
python scripts/odds_shop.py --from-file snapshot.json
python -m src.bet_log banca|list|settle|summary

# Testes
python -m pytest            # suíte Python atual; contagem canônica no HANDOFF
python scripts/ci_check.py  # 5 barreiras

# Backup operacional consistente (destino deve ser uma raiz nova)
python -m src.backup_restore create --output C:\backups\brasileirao-AAAA-MM-DD
python -m src.backup_restore verify --backup C:\backups\brasileirao-AAAA-MM-DD
python -m src.backup_restore restore --backup C:\backups\brasileirao-AAAA-MM-DD --destination C:\restore-novo
```

Registros prospectivos novos incluem timestamps exatos de previsão e kickoff,
turno, fonte, preço capturado e fechamento bruto. Registros anteriores
permanecem legados; não são completados retrospectivamente.

## Trials e pré-registro (`data/trials.json`)

O ledger contém 14 trials: H12 é a única comprovada, H13 é a única
pré-registrada vigente e as outras 12 estão fechadas (refutadas,
inconclusivas, substituídas, exploratórias ou informativa). Não manter uma
lista duplicada aqui: nomes, parâmetros, períodos e notas canônicas vivem em
`data/trials.json`; o resumo interpretativo atual fica no `HANDOFF.md`.

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
src/                      # motor (db, ratings, model, backtest, predict, display…)
scripts/
  sync_matches_from_sofascore.py   # espelho sofascore → matches (novo)
  governanca.py                    # harness + TrialRegistry (novo)
  backtest_walkforward.py          # walk-forward por rodadas (novo)
  prever.py, odds_shop.py, ci_check.py, …
data/                     # matches.db, livros jsonl, trials.json (fora do git)
tests/                    # suíte Python; .NET LineupWorker tem suíte própria
```

Histórico da Copa preservado em `data/results_wc2026_historico.jsonl` e no
repositório original `wc-predictor-v2` (intocado).
