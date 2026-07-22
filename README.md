# brasileirao-predictor

Backfill histórico point-in-time é mantido fora de `matches.db`, em raw
imutável, curated SQLite isolado e views de avaliação com clocks de disponibilidade.
Veja `docs/BACKFILL_POINT_IN_TIME.md` e `docs/CLOSING_LINE.md`.

> ## 📌 ESTADO ATUAL (2026-07-10) — fonte da verdade: HANDOFF.md
>
> Projeto criado a partir do **backup limpo do wc-predictor-v2** pós-Copa 2026,
> adaptado para o **Campeonato Brasileiro Série A**. Vendor no predictor_core
> **v1.3.1**. Backtest walk-forward 2024–2025 **CONCLUÍDO em 2026-07-10 com
> veredito NO-GO** (OU2.5: CLV open +19,55% mas IC95 do pnl cruza zero;
> DSR 0,94) — **operação em MODO SOMBRA, zero dinheiro real** até o N crescer
> (2023 + rodadas de 2026). Em 2026-07-20, H3 tinha 7 picks, só 2 maturados:
> pipeline funcional, resultado econômico **inconclusivo** e gate de 100
> liquidados ainda fechado. H2 (picks 1T) validada informativa (79% de acerto).
> Relatório: `docs/RELATORIO_BACKTEST_2026-07-10.md`. Suíte 325 verdes, CI 5/5.

Sistema CLI em Python para previsão e apostas de valor no Brasileirão Série A,
rodando 100% local (Python + SQLite). Fonte única de dados: **Sofascore**
(resultados, placar de intervalo, odds de abertura/fechamento, estatísticas,
xG) — ut_id 325, temporadas 2024/2025/2026. Não existe CSV público equivalente
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
python -m pytest            # 320 verdes
python scripts/ci_check.py  # 5 barreiras

# Backup operacional consistente (destino deve ser uma raiz nova)
python -m src.backup_restore create --output C:\backups\brasileirao-AAAA-MM-DD
python -m src.backup_restore verify --backup C:\backups\brasileirao-AAAA-MM-DD
python -m src.backup_restore restore --backup C:\backups\brasileirao-AAAA-MM-DD --destination C:\restore-novo
```

Desde 2026-07-20, novos registros H3/H5 incluem timestamps exatos de previsão e
kickoff, turno, fonte, abertura, preço capturado e fechamento bruto. Registros
anteriores permanecem legados; não são completados retrospectivamente.

## Hipóteses pré-registradas (data/trials.json)

- **H1** `h1-ou25-edge-2-15-walkforward` — O/U 2,5 gols, janela de edge 2–15%,
  stake fixo. Herdada da Copa (única população com CLV comprovado lá:
  +16,11% open). GO exige PSR ≥ 0,80, IC95_lower > 0, DSR ≥ 0,95.
- **H2** `h2-periodo-1t-conf60` — picks de O/U do 1º tempo com confiança ≥ 60%,
  fração de gols do 1T calibrada forward-only. **Informativa** (sem odds de
  período na base → sem ROI/CLV); valida se acerto real ≥ 60%.

Criar tentativa NOVA exige o atestado do harness de controle positivo
(`data/trials.harness_attestation.json`) — o funil precisa provar que detecta
edge sintético (ataque ×1,3) e rejeita ruído antes de qualquer veredito valer.

## Regras inegociáveis (herdadas da auditoria da Copa)

1. **1X2 nunca** — viés de achatamento estrutural; CLV −15% comprovado.
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
vendor/predictor_core/    # core v1.3.1 (NÃO editar aqui; sync_core --write)
data/                     # matches.db, livros jsonl, trials.json (fora do git)
tests/                    # 320 testes
```

Histórico da Copa preservado em `data/results_wc2026_historico.jsonl` e no
repositório original `wc-predictor-v2` (intocado).
