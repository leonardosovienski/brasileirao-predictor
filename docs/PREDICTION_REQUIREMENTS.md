# Protocolo do que precisa para prever

Versão: `prediction-readiness/1`
Implementação: `brasileirao_predictor/prediction_protocol.py` e `brasileirao_scripts/check_prediction_readiness.py`.

## Gate obrigatório

O documento JSON de entrada precisa conter:

- identidade: `event_id`, `home`, `away`, `kickoff_at`;
- emissão: `prediction_kind`, `predicted_at`;
- reprodutibilidade: `model_name`, `model_version`, `pipeline_fingerprint`;
- corte PIT: `historical_data_cutoff`, último kickoff usado e horário em que seu resultado ficou disponível;
- completude: número de jogos da temporada corrente incluídos e número elegível disponível;
- governança: `capital_enabled=false` e live features não validadas desativadas.

Para pré-jogo, `predicted_at < kickoff_at` e `lineup_confirmed` deve ser `true` ou `false`, nunca desconhecido. Capturas de escalação e odds posteriores a `predicted_at` bloqueiam a emissão.

Para live, são obrigatórios `live_observed_at`, `observed_minute` e `current_score`. A observação não pode ser futura. Features ao vivo sem pesos validados bloqueiam o cálculo.

Escalação ou odds ausentes geram aviso, não falsificação: a previsão pode existir, mas deve declarar a ausência. Comparação com mercado só é permitida quando houver snapshot PIT.

## Exemplo mínimo pré-jogo

```json
{
  "prediction_kind": "PRE_MATCH",
  "event_id": "123",
  "home": "Time A",
  "away": "Time B",
  "predicted_at": "2026-08-22T21:30:00Z",
  "kickoff_at": "2026-08-22T22:00:00Z",
  "model_name": "serving",
  "model_version": "1",
  "pipeline_fingerprint": "sha256:...",
  "historical_data_cutoff": "2026-08-22T21:30:00Z",
  "latest_training_match_kickoff": "2026-08-21T23:00:00Z",
  "latest_training_result_available_at": "2026-08-22T01:00:00Z",
  "current_season_matches_included": 225,
  "current_season_matches_available": 225,
  "lineup_captured_at": "2026-08-22T21:20:00Z",
  "lineup_confirmed": true,
  "odds_captured_at": null,
  "live_observed_at": null,
  "observed_minute": null,
  "current_score": null,
  "unvalidated_live_features_injected": false,
  "capital_enabled": false
}
```

Saída `ready=true` autoriza somente a emissão técnica. Não autoriza aposta, promoção nem uso econômico.
