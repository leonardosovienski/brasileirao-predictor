# Implementação arquitetural — 2026-09-11

O caminho formal de previsão recebe `--formal-context`, `--date`, `--team-aliases` e `--team-catalog`. O contexto contém readiness e uma cotação explícita ou null. Antes do modelo, valida times canônicos, kickoff/data, gate temporal, event_id e quote_id. Não usa aproximação de nomes/datas para buscar cotação formal. Declarações do chamador continuam sem autenticação; não são evidência econômica nem prospectiva homologada.

Previsões formais registram event_id, contexto e prediction_id por conteúdo. `settle --prediction-id` exige correspondência exata, recusa ausência/duplicidade e conserva o caminho histórico. Aliases legados vivem em identity; settlement não importa o módulo de previsão.

`BRASILEIRAO_PROJECT_ROOT` separa dados/configuração dos pacotes instalados; `BRASILEIRAO_RUNTIME_ROOT` aponta para logs e envelopes fora do código. Configuração pode ser indicada por `BRASILEIRAO_CONFIG_PATH`. O payload shadow usa módulos instalados, não caminhos para scripts no checkout. Os passos só executam quando a rotina é explicitamente chamada.

O envelope Ops agora recebe a proveniência em um jobs file durável. O hash do banco representa um backup SQLite consistente com WAL; não é hash apenas do arquivo principal. O recibo declara que um payload posterior pode observar commits posteriores. O caminho de banco da proveniência deve coincidir com a configuração do payload.

Validação delimitada usa times, previsões, resultados e SQLite sintéticos. CI global, H14/H15/H9/A1, serviços, tarefas agendadas e .NET operacional não foram executados. Nenhum parâmetro de modelo foi alterado. Rollback reinstala o pacote anterior preservando logs e identidades já registradas.

A CI delimitada aprovada cobriu Python 3.13/3.14, wheel instalado com shadow `--check`, .NET 10 e Compose sintético, incluindo reconexão Redis e encerramento gracioso. O `prediction_id` formal retorna ao chamador. O envelope shadow usa schema 3 e exige Ops >=4.2.0.

## Entrega arquitetural publicada — 11/09/2026

Versão **0.2.0** publicada: [release e artefatos](https://github.com/leonardosovienski/brasileirao-predictor/releases/tag/v0.2.0). [CI de engenharia aprovada](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34630041002) para a fonte `4dbd35332344000d116ea2ac56903c77e73f9aa2`. Consulte [ARCHITECTURE_IMPLEMENTATION.md](ARCHITECTURE_IMPLEMENTATION.md) para comportamento, migração e limites. Este registro atualiza a entrega de software; estados científicos e registros datados abaixo conservam sua autoridade e contexto histórico.
