# Survey — OSR-20260911-01

**58 candidatos triados; 15 revisões focais de código; um paper com método/tabelas examinados; três ensaios locais sintéticos.** Aprofundamento é por capacidade/trecho: não significa auditoria integral de 15 repositórios. Testes, issues e releases não foram examinados integralmente para todos. Versões fixadas abaixo; páginas de triagem sem SHA são observações mutáveis de 2026-09-11.

O levantamento foi organizado em quatro ondas: modelos/odds; eventos/tracking/fontes; scoring/execução/resultados negativos; contexto brasileiro e buscas em português/espanhol. O [registro](registry.json) detalha rotas, consultas finais, consumo e lacunas. A rodada termina por escopo de entrega e utilidade marginal da triagem; **não foi comprovada saturação formal em duas ondas**.

Quinze chamadas públicas à API GitHub falharam com 403/quota. O caminho foi abandonado; leitura de repositórios públicos por Git/raw não exigiu autenticação, assinatura ou execução de setup externo. Quinze referências têm SHA; 74 recibos de arquivos foram guardados. Fetch não equivale a leitura: as fichas discriminam o que foi realmente examinado. Nenhuma chamada a API de apostas, aquisição de dados ou teste em dados reais ocorreu.

## Triagem unificada

| ID | Referência primária | Tipo | Profundidade / C | Capacidades | Ação |
| --- | --- | --- | --- | --- | --- |
| R001 | [penaltyblog](https://github.com/martineastwood/penaltyblog) | LIBRARY | FOCUSED_CODE_REVIEW / C4 | K01, K03, K06 | VALIDATE |
| R002 | [goalmodel](https://github.com/opisthokonta/goalmodel) | LIBRARY | FOCUSED_CODE_REVIEW / C1 | K01, K06 | VALIDATE |
| R003 | [footBayes](https://github.com/LeoEgidi/footBayes) | LIBRARY | FOCUSED_CODE_REVIEW / C1 | K06, K07 | RESEARCH |
| R004 | [soccerdata](https://github.com/probberechts/soccerdata) | LIBRARY | FOCUSED_CODE_REVIEW / C1 | K02, K08 | AUGMENT |
| R005 | [socceraction](https://github.com/ML-KULeuven/socceraction) | LIBRARY | FOCUSED_CODE_REVIEW / C2 | K09 | RESEARCH |
| R006 | [kloppy](https://github.com/PySport/kloppy) | LIBRARY | FOCUSED_CODE_REVIEW / C1 | K09 | AUGMENT |
| R007 | [mplsoccer](https://github.com/andrewRowlinson/mplsoccer) | LIBRARY | FOCUSED_CODE_REVIEW / C1 | K10 | AUGMENT |
| R008 | [floodlight](https://github.com/floodlight-sports/floodlight) | LIBRARY | FOCUSED_CODE_REVIEW / C2 | K09 | RESEARCH |
| R009 | [databallpy](https://github.com/Alek050/databallpy) | LIBRARY | FOCUSED_CODE_REVIEW / C1 | K09 | RESEARCH |
| R010 | [shin](https://github.com/mberk/shin) | LIBRARY | FOCUSED_CODE_REVIEW / C2 | K03 | VALIDATE |
| R011 | [implied](https://github.com/opisthokonta/implied) | LIBRARY | FOCUSED_CODE_REVIEW / C1 | K03 | VALIDATE |
| R012 | [flumine](https://github.com/betcode-org/flumine) | FRAMEWORK | FOCUSED_CODE_REVIEW / C2 | K05 | RESEARCH |
| R013 | [betfair](https://github.com/betcode-org/betfair) | FRAMEWORK | FOCUSED_CODE_REVIEW / C1 | K05 | KEEP |
| R014 | [scoringrules](https://github.com/frazane/scoringrules) | LIBRARY | FOCUSED_CODE_REVIEW / C2 | K04 | VALIDATE |
| R015 | [unravelsports](https://github.com/UnravelSports/unravelsports) | LIBRARY | FOCUSED_CODE_REVIEW / C1 | K09 | RESEARCH |
| R016 | [Hudl/StatsBomb Open Data](https://github.com/hudl/open-data) | DATASET | PRIMARY_PAGE_OR_ABSTRACT / C0 | K09 | RESEARCH |
| R017 | [statsbombpy](https://github.com/hudl/statsbombpy) | LIBRARY | PRIMARY_PAGE_OR_ABSTRACT / C0 | K08 | RESEARCH |
| R018 | [Metrica sample-data](https://github.com/metrica-sports/sample-data) | DATASET | PRIMARY_PAGE_OR_ABSTRACT / C0 | K09 | RESEARCH |
| R019 | [SkillCorner opendata](https://github.com/SkillCorner/opendata) | DATASET | PRIMARY_PAGE_OR_ABSTRACT / C0 | K09 | RESEARCH |
| R020 | [Wyscout public dataset / Pappalardo](https://doi.org/10.1038/s41597-019-0247-7) | DATASET | PRIMARY_PAGE_OR_ABSTRACT / C0 | K09 | RESEARCH |
| R021 | [Football-Data.co.uk](https://www.football-data.co.uk/data.php) | DATA_SOURCE | PRIMARY_PAGE_OR_ABSTRACT / C0 | K08 | VALIDATE |
| R022 | [football-data.org](https://www.football-data.org/coverage) | DATA_SOURCE | PRIMARY_PAGE_OR_ABSTRACT / C0 | K08 | RESEARCH |
| R023 | [ClubElo](https://soccerdata.readthedocs.io/en/latest/datasources/ClubElo.html) | DATA_SOURCE | PRIMARY_PAGE_OR_ABSTRACT / C0 | K06 | RESEARCH |
| R024 | [Understat](https://soccerdata.readthedocs.io/en/latest/datasources/Understat.html) | DATA_SOURCE | PRIMARY_PAGE_OR_ABSTRACT / C0 | K07 | RESEARCH |
| R025 | [FBref / Sports Reference](https://www.sports-reference.com/blog/category/advanced-stats/) | DATA_SOURCE | PRIMARY_PAGE_OR_ABSTRACT / C0 | K08 | RESEARCH |
| R026 | [worldfootballR](https://github.com/JaseZiv/worldfootballR) | LIBRARY | PRIMARY_PAGE_OR_ABSTRACT / C0 | K08 | REJECT |
| R027 | [openfootball football.json](https://github.com/openfootball/football.json) | DATASET | PRIMARY_PAGE_OR_ABSTRACT / C0 | K08 | RESEARCH |
| R028 | [SoccerNet](https://github.com/SoccerNet/SoccerNet) | DATASET | PRIMARY_PAGE_OR_ABSTRACT / C0 | K09 | RESEARCH |
| R029 | [soccer_xg](https://github.com/ML-KULeuven/soccer_xg) | LIBRARY | PRIMARY_PAGE_OR_ABSTRACT / C0 | K07 | RESEARCH |
| R030 | [LaurieOnTracking](https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking) | REFERENCE_IMPLEMENTATION | PRIMARY_PAGE_OR_ABSTRACT / C0 | K09 | RESEARCH |
| R031 | [soccermatics](https://github.com/JoGall/soccermatics) | LIBRARY | PRIMARY_PAGE_OR_ABSTRACT / C0 | K10 | RESEARCH |
| R032 | [piratings](https://github.com/larsvancutsem/piratings) | LIBRARY | PRIMARY_PAGE_OR_ABSTRACT / C0 | K06 | RESEARCH |
| R033 | [Bayesian football / period-specific shrinkage](https://arxiv.org/html/2508.05891v1) | PAPER | METHOD_REVIEW / C0 | K06 | RESEARCH |
| R034 | [xG bias across player subgroups](https://arxiv.org/abs/2401.09940) | PAPER | PRIMARY_PAGE_OR_ABSTRACT / C0 | K07 | VALIDATE |
| R035 | [Computations 14(9),195 / comparação com odds](https://www.mdpi.com/2079-3197/14/9/195) | PAPER | PRIMARY_PAGE_OR_ABSTRACT / C0 | K12 | RESEARCH |
| R036 | [Football statistical forecasting / arXiv 2001.09097](https://arxiv.org/abs/2001.09097) | PAPER | PRIMARY_PAGE_OR_ABSTRACT / C0 | K06 | RESEARCH |
| R037 | [Football event sequences / arXiv 2402.06820](https://arxiv.org/abs/2402.06820) | PAPER | PRIMARY_PAGE_OR_ABSTRACT / C0 | K09 | RESEARCH |
| R038 | [Shot quantity and quality / arXiv 2501.05873](https://arxiv.org/abs/2501.05873) | PAPER | PRIMARY_PAGE_OR_ABSTRACT / C0 | K07 | RESEARCH |
| R039 | [pi-football Bayesian network](https://www.sciencedirect.com/science/article/pii/S0950705112001967) | PAPER | PRIMARY_PAGE_OR_ABSTRACT / C0 | K06 | RESEARCH |
| R040 | [scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html) | FRAMEWORK | PRIMARY_PAGE_OR_ABSTRACT / C0 | K04 | VALIDATE |
| R041 | [PyMC](https://github.com/pymc-devs/pymc) | FRAMEWORK | PRIMARY_PAGE_OR_ABSTRACT / C0 | K06 | RESEARCH |
| R042 | [NumPyro](https://github.com/pyro-ppl/numpyro) | FRAMEWORK | PRIMARY_PAGE_OR_ABSTRACT / C0 | K06 | RESEARCH |
| R043 | [Stan](https://github.com/stan-dev/stan) | FRAMEWORK | PRIMARY_PAGE_OR_ABSTRACT / C0 | K06 | RESEARCH |
| R044 | [XGBoost](https://github.com/dmlc/xgboost) | LIBRARY | PRIMARY_PAGE_OR_ABSTRACT / C0 | K11 | RESEARCH |
| R045 | [LightGBM](https://github.com/lightgbm-org/LightGBM) | LIBRARY | PRIMARY_PAGE_OR_ABSTRACT / C0 | K11 | RESEARCH |
| R046 | [CatBoost](https://github.com/catboost/catboost) | LIBRARY | PRIMARY_PAGE_OR_ABSTRACT / C0 | K11 | RESEARCH |
| R047 | [Optuna](https://github.com/optuna/optuna) | TOOL | PRIMARY_PAGE_OR_ABSTRACT / C0 | K11 | RESEARCH |
| R048 | [Pandera](https://github.com/unionai-oss/pandera) | TOOL | PRIMARY_PAGE_OR_ABSTRACT / C0 | K02 | AUGMENT |
| R049 | [MLflow](https://mlflow.org/docs/latest/) | TOOL | PRIMARY_PAGE_OR_ABSTRACT / C0 | K10 | KEEP |
| R050 | [MAPIE](https://github.com/scikit-learn-contrib/MAPIE) | LIBRARY | PRIMARY_PAGE_OR_ABSTRACT / C0 | K04 | RESEARCH |
| R051 | [The Odds API historical](https://the-odds-api.com/historical-odds-data/) | DATA_SOURCE | PRIMARY_PAGE_OR_ABSTRACT / C0 | K08 | RESEARCH |
| R052 | [Sportmonks v3](https://docs.sportmonks.com/v3) | DATA_SOURCE | PRIMARY_PAGE_OR_ABSTRACT / C0 | K08 | RESEARCH |
| R053 | [API-Football](https://www.api-football.com/documentation-v3) | DATA_SOURCE | PRIMARY_PAGE_OR_ABSTRACT / C0 | K08 | RESEARCH |
| R054 | [dk3yyyy football_predictor](https://github.com/dk3yyyy/football_predictor) | PROJECT | PRIMARY_PAGE_OR_ABSTRACT / C0 | K11 | RESEARCH |
| R055 | [roni-altshuler soccer_predictor](https://github.com/roni-altshuler/soccer_predictor) | PROJECT | PRIMARY_PAGE_OR_ABSTRACT / C0 | K11 | RESEARCH |
| R056 | [jkrusina SoccerPredictor](https://github.com/jkrusina/SoccerPredictor) | PROJECT | PRIMARY_PAGE_OR_ABSTRACT / C0 | K11 | RESEARCH |
| R057 | [FootballGPT football-model](https://github.com/FootballGPT/football-model) | PROJECT | PRIMARY_PAGE_OR_ABSTRACT / C0 | K11 | RESEARCH |
| R058 | [CBF calendário nacional 2026](https://www.cbf.com.br/a-cbf/noticias/informes-cbf/a/cbf-anuncia-novo-calendario-do-futebol-profissional-masculino) | DATA_SOURCE | PRIMARY_PAGE_OR_ABSTRACT / C0 | K07 | RESEARCH |


## Quinze fichas focais

C0 = alegação; C1 = código relevante lido; C2 = asserções pertinentes lidas; C3 = execução registrada; C4 = comparação controlada. Marcos E são registrados por claim: E1 implementação, E2 linhagens examinadas, E3 estudo analisado, E5 reprodução local. C4/E5 nos casos sintéticos não implica E6, boa previsão ou lucro. Não se promove uma biblioteca inteira ao nível do melhor trecho.


### R001 — martineastwood/penaltyblog

Versão `1.12.1`; SHA `15ebb8a299fa75524ac57e32f3778f174bd5b42b`; commit observado `2026-09-10T13:41:50+01:00`. Licença de código declarada **MIT**, ambiente **>=3.10**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [penaltyblog/implied/implied.py](https://github.com/martineastwood/penaltyblog/blob/15ebb8a299fa75524ac57e32f3778f174bd5b42b/penaltyblog/implied/implied.py) (completo); [penaltyblog/implied/models.py](https://github.com/martineastwood/penaltyblog/blob/15ebb8a299fa75524ac57e32f3778f174bd5b42b/penaltyblog/implied/models.py) (completo); [penaltyblog/models/football_probability_grid.py](https://github.com/martineastwood/penaltyblog/blob/15ebb8a299fa75524ac57e32f3778f174bd5b42b/penaltyblog/models/football_probability_grid.py) (1–130; 200–350); [test/test_implied.py](https://github.com/martineastwood/penaltyblog/blob/15ebb8a299fa75524ac57e32f3778f174bd5b42b/test/test_implied.py) (1–130). Shin e power comparados somente por dois módulos copiados; T02. Os testes externos foram lidos, não executados como suíte. Nível **C4** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Nos dez pares que retornaram dos dois lados, diferença máxima 4,63e-13. Shin falha em underround e power falha no stress 1.001. O dataclass aceita probabilidade negativa se a soma passa. A grade externa não é um oráculo universal.

**Dados e mecanismo:** odds sintéticas ou pares nomeados e contemporâneos; dados de futebol para modelos não usados. Capacidades K01, K03, K06; nenhuma demonstração de eficácia preditiva/econômica local. Ação **VALIDATE**, estado **BENCHMARKED_ENGINEERING**. Referência diferencial estreita; não substituir biblioteca inteira nem importar scraper ou backtest.


### R002 — opisthokonta/goalmodel

Versão `0.6.4`; SHA `84ecd6c2bbad3ccb967abf88ef49e5bcd074e545`; commit observado `2024-03-30T20:51:18+01:00`. Licença de código declarada **GPL-3.0**, ambiente **R**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [R/dixoncoles.R](https://github.com/opisthokonta/goalmodel/blob/84ecd6c2bbad3ccb967abf88ef49e5bcd074e545/R/dixoncoles.R) (completo); [README.md](https://github.com/opisthokonta/goalmodel/blob/84ecd6c2bbad3ccb967abf88ef49e5bcd074e545/README.md) (seções de modelos e correção DC); [NEWS.md](https://github.com/opisthokonta/goalmodel/blob/84ecd6c2bbad3ccb967abf88ef49e5bcd074e545/NEWS.md) (nota de correção de defesa; versão observada no repositório). Correção de quatro células e interfaces Poisson/DC lidas; nenhum ajuste R executado. Nível **C1** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Ajuda a comparar convenção de rho e low scores. A nota de correção de defesa mostra por que a versão importa; não constitui reprodução dos resultados do pacote.

**Dados e mecanismo:** histórico de gols com mando e cronologia. Capacidades K01, K06; nenhuma demonstração de eficácia preditiva/econômica local. Ação **VALIDATE**, estado **CODE_REVIEWED**. Usar fórmula e casos analíticos em referência separada; revisar obrigações GPL antes de redistribuir implementação derivada.


### R003 — LeoEgidi/footBayes

Versão `2.1.0`; SHA `00540f5ae12b9dd6a4d97c5be228fb72c4be4b0d`; commit observado `2026-09-09T17:36:49+02:00`. Licença de código declarada **GPL-2.0**, ambiente **R / Stan compilado**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [src/stan/dixon_coles_dynamic.stan](https://github.com/LeoEgidi/footBayes/blob/00540f5ae12b9dd6a4d97c5be228fb72c4be4b0d/src/stan/dixon_coles_dynamic.stan) (1–190); [DESCRIPTION](https://github.com/LeoEgidi/footBayes/blob/00540f5ae12b9dd6a4d97c5be228fb72c4be4b0d/DESCRIPTION) (metadados). Modelo dinâmico Stan, priors, parametrização não centrada e restrição de rho examinados parcialmente. Nível **C1** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Pooling temporal pode regularizar equipes com pouco histórico. Limites de rho e posterior exigem validação para todos os confrontos previstos; ler likelihood não demonstra convergência nem calibração brasileira.

**Dados e mecanismo:** resultados PIT, identidades estáveis, temporadas e orçamento MCMC. Capacidades K06, K07; nenhuma demonstração de eficácia preditiva/econômica local. Ação **RESEARCH**, estado **CONDITIONAL**. Processo de pesquisa R/Stan separado; não portar parâmetros europeus. Paper R033 e pacote não são replicações independentes.


### R004 — probberechts/soccerdata

Versão `1.9.1`; SHA `e120471e424a173e83e8aeeaaf4d954ab9d38ee4`; commit observado `2026-08-06T01:07:55Z`. Licença de código declarada **Apache-2.0**, ambiente **>=3.10,<3.15**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [soccerdata/understat.py](https://github.com/probberechts/soccerdata/blob/e120471e424a173e83e8aeeaaf4d954ab9d38ee4/soccerdata/understat.py) (1–100); [README.rst](https://github.com/probberechts/soccerdata/blob/e120471e424a173e83e8aeeaaf4d954ab9d38ee4/README.rst) (fontes e instalação). Construtor/importador Understat e uso de cache inspecionados; scrapers não executados. Nível **C1** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Unifica interfaces, mas não confere licença dos dados, cobertura brasileira ou recibos históricos. Mudanças de provedores e falhas de FBref impedem tratar instalação como coleta garantida.

**Dados e mecanismo:** acesso autorizado e cobertura campo a campo do provedor. Capacidades K02, K08; nenhuma demonstração de eficácia preditiva/econômica local. Ação **AUGMENT**, estado **CONDITIONAL**. Adapter por fonte com identidade e relógios; não instalar para preencher dados supostamente ausentes.


### R005 — ML-KULeuven/socceraction

Versão `1.5.3`; SHA `93a1242d46c104889205753accaabadb00c45c6d`; commit observado `2026-01-07T09:40:04+01:00`. Licença de código declarada **MIT**, ambiente **>=3.9,<3.13; numpy ^1.26**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [socceraction/xthreat.py](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/xthreat.py) (141–320); [tests/test_xthreat.py](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/tests/test_xthreat.py) (1–75); [pyproject.toml](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/pyproject.toml) (metadados e dependências). Probabilidades de ações, transições e iteração de valor xT lidas; testes de coordenadas fora da grade examinados. Nível **C2** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Probabilidade de transição inclui falhas no denominador; limites espaciais e taxonomia alteram xT. Release 1.5.3 registra correção atomic-VAEP. Requer Python fora do intervalo atual do beneficiário.

**Dados e mecanismo:** eventos SPADL, treino sem futuro, versão de coordenadas e minutos. Capacidades K09; nenhuma demonstração de eficácia preditiva/econômica local. Ação **RESEARCH**, estado **BLOCKED_DATA_RUNTIME**. Apenas laboratório separado após contrato de eventos; VAEP e xT não são forecasts pré-jogo prontos.


### R006 — PySport/kloppy

Versão `3.19.0`; SHA `51dbd38c4fb48c0815119e23ff9a3a68ea06be52`; commit observado `2026-08-06T14:46:36+02:00`. Licença de código declarada **BSD-3-Clause**, ambiente **>=3.9**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [kloppy/domain/services/transformers/dataset.py](https://github.com/PySport/kloppy/blob/51dbd38c4fb48c0815119e23ff9a3a68ea06be52/kloppy/domain/services/transformers/dataset.py) (1–180); [kloppy/tests/test_statsbomb.py](https://github.com/PySport/kloppy/blob/51dbd38c4fb48c0815119e23ff9a3a68ea06be52/kloppy/tests/test_statsbomb.py) (1–100). Transformador espacial/orientação lido; testes iniciais de enumeração e fixture StatsBomb inspecionados, não testes suficientes do transformador. Nível **C1** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Expõe orientação e dimensões de origem/destino. Fixture de teste usa URL master mutável e rede: não é benchmark offline congelado. Ter parser não resolve clock de publicação.

**Dados e mecanismo:** eventos/tracking e dimensões/orientação por período. Capacidades K09; nenhuma demonstração de eficácia preditiva/econômica local. Ação **AUGMENT**, estado **CODE_REVIEWED**. Preferir contrato de coordenadas a parser próprio; congelar fixtures admissíveis antes de executar.


### R007 — andrewRowlinson/mplsoccer

Versão `UNKNOWN (dinâmica)`; SHA `ad40c4ccbade56263ccd1d038ad49044fa9928d8`; commit observado `2026-07-31T13:40:36-07:00`. Licença de código declarada **MIT**, ambiente **>=3.10**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [mplsoccer/soccer/statsbomb.py](https://github.com/andrewRowlinson/mplsoccer/blob/ad40c4ccbade56263ccd1d038ad49044fa9928d8/mplsoccer/soccer/statsbomb.py) (1–115); [pyproject.toml](https://github.com/andrewRowlinson/mplsoccer/blob/ad40c4ccbade56263ccd1d038ad49044fa9928d8/pyproject.toml) (metadados). Leitura limitada ao parser StatsBomb; nenhuma figura externa renderizada. Nível **C1** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Útil para inspeção visual; trecho usa URL master e requests.get sem timeout explícito. Não é evidência de previsão nem motivo para trocar arquitetura.

**Dados e mecanismo:** eventos ou coordenadas já admissíveis. Capacidades K10; nenhuma demonstração de eficácia preditiva/econômica local. Ação **AUGMENT**, estado **CODE_REVIEWED**. Exportar diagnósticos apenas se responderem questão concreta; não criar dashboard permanente nesta rodada.


### R008 — floodlight-sports/floodlight

Versão `1.2.0`; SHA `699b7fa1e37f6de2351079d64508551bf5fb9ad7`; commit observado `2026-05-04T17:33:58+02:00`. Licença de código declarada **MIT**, ambiente **>=3.10,<3.14**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [floodlight/transforms/temporal.py](https://github.com/floodlight-sports/floodlight/blob/699b7fa1e37f6de2351079d64508551bf5fb9ad7/floodlight/transforms/temporal.py) (1–130); [tests/test_transforms/test_temporal.py](https://github.com/floodlight-sports/floodlight/blob/699b7fa1e37f6de2351079d64508551bf5fb9ad7/tests/test_transforms/test_temporal.py) (1–105). Resampling e asserções de identidade, downsample, linear e polynomial examinados. Nível **C2** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Testes preservam metadados e cópia na identidade; interpolação muda valores e pode ultrapassar coordenadas de entrada. Não tratar pontos interpolados como medições.

**Dados e mecanismo:** tracking com frequência, lacunas e clocks de captura. Capacidades K09; nenhuma demonstração de eficácia preditiva/econômica local. Ação **RESEARCH**, estado **CONDITIONAL**. Comparar apenas quando tracking justificar; Python 3.14 não está no intervalo declarado.


### R009 — Alek050/databallpy

Versão `0.8.1`; SHA `3a8ebc17c6c752fb6e087069eeb707f60d2b9841`; commit observado `2026-08-11T13:17:25+02:00`. Licença de código declarada **MIT**, ambiente **>=3.10,<3.15**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [databallpy/utils/synchronise_tracking_and_event_data.py](https://github.com/Alek050/databallpy/blob/3a8ebc17c6c752fb6e087069eeb707f60d2b9841/databallpy/utils/synchronise_tracking_and_event_data.py) (1–130); [pyproject.toml](https://github.com/Alek050/databallpy/blob/3a8ebc17c6c752fb6e087069eeb707f60d2b9841/pyproject.toml) (metadados). Entrada da sincronização e chamada Needleman–Wunsch/batching inspecionadas; núcleo completo e testes não lidos. Nível **C1** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Separar erro de alinhamento do erro de modelo. Documentação limita tipos usados no alinhamento; cartões não ganham sincronização só porque outros eventos ganham.

**Dados e mecanismo:** eventos mais tracking do mesmo jogo e âncoras temporais. Capacidades K09; nenhuma demonstração de eficácia preditiva/econômica local. Ação **RESEARCH**, estado **CONDITIONAL**. Método candidato para medir erro de alinhamento, sem adoção imediata.


### R010 — mberk/shin

Versão `0.2.2`; SHA `ae460853fabeca7d512bbf7de8aaa55dc17f3485`; commit observado `2025-10-23T20:12:20+09:00`. Licença de código declarada **MIT**, ambiente **>=3.9**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [python/shin/__init__.py](https://github.com/mberk/shin/blob/ae460853fabeca7d512bbf7de8aaa55dc17f3485/python/shin/__init__.py) (completo); [tests/test_shin.py](https://github.com/mberk/shin/blob/ae460853fabeca7d512bbf7de8aaa55dc17f3485/tests/test_shin.py) (1–105). Solver iterativo Python e ramo n=2 lidos; testes com valores conhecidos e caminhos Python/native examinados. Nível **C2** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Expõe iterações, delta e z; tem referência alternativa ao root solver scipy. Rust/native não executado. Mesma equação de Shin não significa evidência independente de preço justo.

**Dados e mecanismo:** vetores de odds mutuamente exclusivos e exaustivos. Capacidades K03; nenhuma demonstração de eficácia preditiva/econômica local. Ação **VALIDATE**, estado **TESTS_INSPECTED**. Candidato a terceira implementação em N02; validar sem baixar/rodar engine completo automaticamente.


### R011 — opisthokonta/implied

Versão `0.6.1`; SHA `1d1c5cd548dd71bc1b9addd733db5c2db8566b71`; commit observado `2026-05-23T20:59:40+02:00`. Licença de código declarada **GPL-3.0**, ambiente **R**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [R/implied_probabilities.R](https://github.com/opisthokonta/implied/blob/1d1c5cd548dd71bc1b9addd733db5c2db8566b71/R/implied_probabilities.R) (1–170); [DESCRIPTION](https://github.com/opisthokonta/implied/blob/1d1c5cd548dd71bc1b9addd733db5c2db8566b71/DESCRIPTION) (metadados). Documentação de métodos e validação/matriz iniciais examinadas; não todo solver. Nível **C1** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Vários métodos e opções não demonstram qual é melhor no Brasileirão. Política de underround deve ser explícita, não escondida como falha numérica.

**Dados e mecanismo:** odds admissíveis e documentação do método. Capacidades K03; nenhuma demonstração de eficácia preditiva/econômica local. Ação **VALIDATE**, estado **CODE_REVIEWED**. Usar como contraste de convenções e manter lineage com goalmodel do mesmo autor.


### R012 — betcode-org/flumine

Versão `UNKNOWN (dinâmica)`; SHA `54854495b45accae614b23d10859047d582c3ecf`; commit observado `2026-09-07T17:58:51+01:00`. Licença de código declarada **MIT**, ambiente **>=3.10**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [flumine/simulation/simulatedorder.py](https://github.com/betcode-org/flumine/blob/54854495b45accae614b23d10859047d582c3ecf/flumine/simulation/simulatedorder.py) (1–155); [tests/test_simulatedorder.py](https://github.com/betcode-org/flumine/blob/54854495b45accae614b23d10859047d582c3ecf/tests/test_simulatedorder.py) (1–100). Estado de mercado/runner, matching e atraso lidos; testes iniciais de estado e dispatch examinados, não de todo lay/comissão. Nível **C2** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Tem conceitos além do simulador back binário local. Isso não comprova acesso ou fills do usuário. Compartilha dependência/linhagem com betfairlightweight.

**Dados e mecanismo:** livro e regras históricas nominais; aceitação e limite desconhecidos. Capacidades K05; nenhuma demonstração de eficácia preditiva/econômica local. Ação **RESEARCH**, estado **CONDITIONAL**. Extrair requisitos; não conectar exchange, criar conta ou simulação recorrente.


### R013 — betcode-org/betfair

Versão `UNKNOWN (dinâmica)`; SHA `b00072113e9a1017d5b9cc705e9d1d3444a91036`; commit observado `2026-09-04T08:42:05+01:00`. Licença de código declarada **MIT**, ambiente **>=3.9**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [betfairlightweight/filters.py](https://github.com/betcode-org/betfair/blob/b00072113e9a1017d5b9cc705e9d1d3444a91036/betfairlightweight/filters.py) (1–90). Filtros de stream, ladder depth, ordem e intervalo de tempo inspecionados. Nível **C1** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** SDK oferece transporte e seleção de campos, não hipótese de alpha. Código de autenticação e execução não foi auditado ou chamado.

**Dados e mecanismo:** conta, feed e direitos não acessados. Capacidades K05; nenhuma demonstração de eficácia preditiva/econômica local. Ação **KEEP**, estado **REFERENCE_ONLY**. Referência de contrato apenas; não acoplar SDK ao kernel nesta rodada.


### R014 — frazane/scoringrules

Versão `0.11.0`; SHA `e48aa74fdbf2d916ade569e1b7516286dbc8b303`; commit observado `2026-06-20T21:53:41+02:00`. Licença de código declarada **Apache-2.0**, ambiente **>=3.12**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [scoringrules/core/brier.py](https://github.com/frazane/scoringrules/blob/e48aa74fdbf2d916ade569e1b7516286dbc8b303/scoringrules/core/brier.py) (completo); [tests/test_brier.py](https://github.com/frazane/scoringrules/blob/e48aa74fdbf2d916ade569e1b7516286dbc8b303/tests/test_brier.py) (1–100). Fórmulas e asserções de Brier/RPS inspecionadas. Nível **C2** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Brier binário elemento a elemento e RPS cumulativo exigem adapter para Brier multiclasses soma 0–2 local. Igual nome não garante denominador comparável.

**Dados e mecanismo:** probabilidades e labels sintéticos bastam ao teste de engenharia. Capacidades K04; nenhuma demonstração de eficácia preditiva/econômica local. Ação **VALIDATE**, estado **TESTS_INSPECTED**. Fixar ordem 1/X/2, clipping e redução antes de diferencial.


### R015 — UnravelSports/unravelsports

Versão `UNKNOWN (dinâmica)`; SHA `2bd24d7e2b3cc19cbdba6486c7abb70270a732ad`; commit observado `2026-01-16T11:14:35+01:00`. Licença de código declarada **MPL-2.0**, ambiente **UNKNOWN**. Licença de dados/serviço é separada e não foi presumida. A data de commit não certifica manutenção futura.

**Inspecionado:** [unravel/soccer/models/pressing_intensity.py](https://github.com/UnravelSports/unravelsports/blob/2bd24d7e2b3cc19cbdba6486c7abb70270a732ad/unravel/soccer/models/pressing_intensity.py) (1–268). Estrutura e cálculo parcial de intensidade de pressão inspecionados; testes não lidos. Nível **C1** estritamente nesse escopo. CI externa não executada; sweep de issues/releases parcial. Arquivos adicionais baixados não recebem CODE_VERIFIED automaticamente.

**CODE_VERIFIED / limite:** Modela geometria, velocidades, equipes e máscaras. Exemplos de outro esporte não validam futebol; grafos e pressão dependem de tracking e convenções locais.

**Dados e mecanismo:** tracking com velocidade, posse e identidade; kloppy/polars. Capacidades K09; nenhuma demonstração de eficácia preditiva/econômica local. Ação **RESEARCH**, estado **CONDITIONAL**. Adiar modelo complexo; testar coordenadas e missingness primeiro.


## Ficha metodológica — R033

O [paper em versão v1](https://arxiv.org/html/2508.05891v1) foi examinado nos métodos e tabelas: shrinkage por períodos, modelos dinâmicos, três ligas europeias e cinco temporadas. A tabela 2 traz exemplo EPL em que DIBP ponderado fica em 0,594 versus 0,588 do comparador, portanto a superioridade não é uniforme. Não foi demonstrada comparação com odds contemporâneas sob o mesmo contrato. A implicação é testar regularização causal como hipótese; não transferir parâmetros ou inferir lucro. Autores/pacote footBayes compartilham linhagem. E3 externo, resultado heterogêneo; sem reprodução local ou E4 independente.

## Demais fichas de triagem

O texto abaixo preserva o nível documental e o motivo da decisão. Versão, licença, manutenção e testes ficam UNKNOWN/NOT_INSPECTED quando não foram verificados; isso impede pontuar qualidade de código por README.


- **R016 — [Hudl/StatsBomb Open Data](https://github.com/hudl/open-data)**: Eventos e lineups abertos; índice de competições consultado não confirmou Brasileirão. Histórico publicado depois não prova disponibilidade pré-jogo. Ação RESEARCH; C0; TRIAGED.

- **R017 — [statsbombpy](https://github.com/hudl/statsbombpy)**: Cliente de API e open data; termos do serviço/dataset separados. README consultado; código não auditado. Ação RESEARCH; C0; TRIAGED.

- **R018 — [Metrica sample-data](https://github.com/metrica-sports/sample-data)**: Amostras de eventos/tracking para desenvolver validação espacial; não série brasileira admissível demonstrada. Ação RESEARCH; C0; TRIAGED.

- **R019 — [SkillCorner opendata](https://github.com/SkillCorner/opendata)**: README anuncia dez jogos A-League 2024/25; tracking 10fps distingue detectado/extrapolado; filtro de minutos afeta agregados. Não comprova transferência brasileira. Ação RESEARCH; C0; TRIAGED.

- **R020 — [Wyscout public dataset / Pappalardo](https://doi.org/10.1038/s41597-019-0247-7)**: Conjunto público de eventos descrito em paper; página principal falhou. Metadados/abstract e referência autoral apenas; termos e campos pendentes. Ação RESEARCH; C0; TRIAGED.

- **R021 — [Football-Data.co.uk](https://www.football-data.co.uk/data.php)**: Página Brazil oferece histórico; aviso sobre Pinnacle desde 23/07/2025 confirmado. Closing e agregados não são recibos de execução. CSVs não baixados. Ação VALIDATE; C0; TRIAGED.

- **R022 — [football-data.org](https://www.football-data.org/coverage)**: Cobertura oficial lista Brazil Série A no free tier. API não chamada; campos, seasons, quotas e histórico PIT não demonstrados. É fonte diferente de .co.uk. Ação RESEARCH; C0; TRIAGED.

- **R023 — [ClubElo](https://soccerdata.readthedocs.io/en/latest/datasources/ClubElo.html)**: Referência de ratings europeus via documentação do adapter; cobertura brasileira não confirmada. Ação RESEARCH; C0; TRIAGED.

- **R024 — [Understat](https://soccerdata.readthedocs.io/en/latest/datasources/Understat.html)**: xG de ligas estrangeiras; documentação do cliente não prova cobertura Brasil ou relógio de revisão. Ação RESEARCH; C0; TRIAGED.

- **R025 — [FBref / Sports Reference](https://www.sports-reference.com/blog/category/advanced-stats/)**: Comunicado primário de janeiro de 2026 informa retirada de advanced stats. Artigo específico retornou 403; não estender a toda informação do site. Ação RESEARCH; C0; TRIAGED.

- **R026 — [worldfootballR](https://github.com/JaseZiv/worldfootballR)**: README informa projeto arquivado e sem manutenção. Não escolher como nova dependência crítica de fonte. Ação REJECT; C0; DEFERRED.

- **R027 — [openfootball football.json](https://github.com/openfootball/football.json)**: Fixtures e resultados em JSON; publicação gerada não fornece por si ingestão histórica ou cutoff do decisor. Ação RESEARCH; C0; TRIAGED.

- **R028 — [SoccerNet](https://github.com/SoccerNet/SoccerNet)**: Vídeo e anotação para tarefas esportivas; previsão pré-jogo não é a mesma tarefa. Ação RESEARCH; C0; TRIAGED.

- **R029 — [soccer_xg](https://github.com/ML-KULeuven/soccer_xg)**: Pipelines xG sobre eventos/SPADL; utilidade downstream depende de treino causal e dados. Código não lido. Ação RESEARCH; C0; TRIAGED.

- **R030 — [LaurieOnTracking](https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking)**: Material de ensino de pitch control; pesquisa geométrica, não predictor econômico validado. Ação RESEARCH; C0; TRIAGED.

- **R031 — [soccermatics](https://github.com/JoGall/soccermatics)**: Visualização R de passes, heatmaps e tracking; alternativa de mesma capacidade, não outro backlog. Ação RESEARCH; C0; TRIAGED.

- **R032 — [piratings](https://github.com/larsvancutsem/piratings)**: DESCRIPTION 0.1.4 GPL-2; rating Pi é controle candidato. Implementação e testes não examinados. Ação RESEARCH; C0; TRIAGED.

- **R033 — [Bayesian football / period-specific shrinkage](https://arxiv.org/html/2508.05891v1)**: Método e tabelas lidos; resultados não uniformes por liga e sem controle de mercado equivalente demonstrado. Ver ficha metodológica. Ação RESEARCH; C0; TRIAGED.

- **R034 — [xG bias across player subgroups](https://arxiv.org/abs/2401.09940)**: Abstract aponta heterogeneidade de viés entre jogadores; auditoria por grupo é hipótese útil. Paper completo não lido. Ação VALIDATE; C0; TRIAGED.

- **R035 — [Computations 14(9),195 / comparação com odds](https://www.mdpi.com/2079-3197/14/9/195)**: Resumo consultado relata dificuldade de superar baseline de mercado sem margem. Resultado externo negativo, não replicado; método completo não auditado. Ação RESEARCH; C0; TRIAGED.

- **R036 — [Football statistical forecasting / arXiv 2001.09097](https://arxiv.org/abs/2001.09097)**: Referência estatística em triagem por abstract; nenhum ganho local inferido. Ação RESEARCH; C0; TRIAGED.

- **R037 — [Football event sequences / arXiv 2402.06820](https://arxiv.org/abs/2402.06820)**: Sequências de eventos e modelos de linguagem: tarefa distinta de vantagem pré-jogo. Abstract apenas. Ação RESEARCH; C0; TRIAGED.

- **R038 — [Shot quantity and quality / arXiv 2501.05873](https://arxiv.org/abs/2501.05873)**: Decompor volume/qualidade é hipótese científica; informações de tiro pós-jogo não são features do próprio jogo. Abstract apenas. Ação RESEARCH; C0; TRIAGED.

- **R039 — [pi-football Bayesian network](https://www.sciencedirect.com/science/article/pii/S0950705112001967)**: Estudo histórico EPL e informação subjetiva; texto completo indisponível. Alegação antiga não prova edge persistente. Ação RESEARCH; C0; TRIAGED.

- **R040 — [scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html)**: Documentação diferencia calibração/resolução e separação de ajuste; não prova modelo vencedor. Ação VALIDATE; C0; TRIAGED.

- **R041 — [PyMC](https://github.com/pymc-devs/pymc)**: Infraestrutura bayesiana alternativa. Discovery documental; código/testes não lidos. Ação RESEARCH; C0; TRIAGED.

- **R042 — [NumPyro](https://github.com/pyro-ppl/numpyro)**: Inferência probabilística com JAX; não algoritmo de futebol comprovado. Ação RESEARCH; C0; TRIAGED.

- **R043 — [Stan](https://github.com/stan-dev/stan)**: Backend probabilístico; licença do backend não se confunde com licença do wrapper R. Ação RESEARCH; C0; TRIAGED.

- **R044 — [XGBoost](https://github.com/dmlc/xgboost)**: Boosting como challenger tabular somente após contrato causal e orçamento igual. Ação RESEARCH; C0; TRIAGED.

- **R045 — [LightGBM](https://github.com/lightgbm-org/LightGBM)**: Alternativa de boosting na mesma família; não independente confirmação de alpha. Ação RESEARCH; C0; TRIAGED.

- **R046 — [CatBoost](https://github.com/catboost/catboost)**: Tratamento de categóricas precisa treino dentro do fold; transferência de times não automática. Ação RESEARCH; C0; TRIAGED.

- **R047 — [Optuna](https://github.com/optuna/optuna)**: Busca de hiperparâmetros exige orçamento e ledger de todas as tentativas; não prioridade instalar. Ação RESEARCH; C0; TRIAGED.

- **R048 — [Pandera](https://github.com/unionai-oss/pandera)**: Schema pode expressar tipos/checks; não certifica causalidade ou recibos reais. Ação AUGMENT; C0; TRIAGED.

- **R049 — [MLflow](https://mlflow.org/docs/latest/)**: Tracking de runs é alternativa a arquivos; novo serviço não justificado nesta rodada. Ação KEEP; C0; TRIAGED.

- **R050 — [MAPIE](https://github.com/scikit-learn-contrib/MAPIE)**: Conformal e controle de risco dependem das premissas; exchangeability não deve ser presumida em futebol temporal. Ação RESEARCH; C0; TRIAGED.

- **R051 — [The Odds API historical](https://the-odds-api.com/historical-odds-data/)**: Histórico documentado; pacote, competição, campos e custo precisam prova antes de qualquer coleta. Nenhuma API chamada. Ação RESEARCH; C0; TRIAGED.

- **R052 — [Sportmonks v3](https://docs.sportmonks.com/v3)**: Portal comercial consultado; cobertura contratada, quotas e disponibilidade brasileira não verificadas. PUBLIC_EVIDENCE_ONLY. Ação RESEARCH; C0; TRIAGED.

- **R053 — [API-Football](https://www.api-football.com/documentation-v3)**: Página não renderizou conteúdo útil; cobertura/custo/PIT UNKNOWN. PUBLIC_EVIDENCE_ONLY. Ação RESEARCH; C0; TRIAGED.

- **R054 — [dk3yyyy football_predictor](https://github.com/dk3yyyy/football_predictor)**: README descreve experimentos temporais e hashes; não houve leitura/execução de código. Não certificar resultados anunciados. Ação RESEARCH; C0; TRIAGED.

- **R055 — [roni-altshuler soccer_predictor](https://github.com/roni-altshuler/soccer_predictor)**: README relata challengers sem ganho. Evidência negativa anunciada, sem reprodução. Ação RESEARCH; C0; TRIAGED.

- **R056 — [jkrusina SoccerPredictor](https://github.com/jkrusina/SoccerPredictor)**: LSTM temporal anunciado; complexidade não demonstra probabilidade ou retorno melhor. Ação RESEARCH; C0; TRIAGED.

- **R057 — [FootballGPT football-model](https://github.com/FootballGPT/football-model)**: Alegações de XGB/NN e grande amostra no README; sem auditoria de splits/preços. Ação RESEARCH; C0; TRIAGED.

- **R058 — [CBF calendário nacional 2026](https://www.cbf.com.br/a-cbf/noticias/informes-cbf/a/cbf-anuncia-novo-calendario-do-futebol-profissional-masculino)**: Comunicado primário confirma mudança de calendário em 2026. Usar versão publicada para contexto; não foram abertos resultados de partidas. Ação RESEARCH; C0; TRIAGED.


## Fontes: cobertura, relógios e acesso

| ID | Cobertura / campos | Temporalidade | Acesso / PIT | Custo, termos e limite |
| --- | --- | --- | --- | --- |
| R021 | Brasil histórico descrito na página; temporadas/campos efetivos não inspecionados; placar e odds decimais; opening/closing/seleções dependem do arquivo | histórico retrospectivo; ingestão antiga não provada | 3 / UNKNOWN | direito de redistribuição/limites não verificados; zero CSVs baixados; Aviso Pinnacle desde 23/07/2025 afeta feed divulgado, não toda a casa. Máximas/médias não são casas simultâneas. |
| R022 | Brazil Série A listada; temporadas/jogos não enumerados; fixtures/equipes; endpoints não chamados | API atual; versões/publication/ingestion UNKNOWN | UNKNOWN / UNKNOWN | free tier documental; quota atual não consultada; Não confundir .org com .co.uk; documento de cobertura não é recibo de campos. |
| R016 | Índice de competições consultado; Série A brasileira não confirmada; eventos, lineups e subsets 360 | release retrospectivo; event time não é available_at | 3 / 1 | PDF de termos não lido; não redistribuir dados; Útil ao método; partidas e labels não ingeridos para avaliação local. |
| R018 | amostra global, Brasil não demonstrado; tracking e eventos | dataset de demonstração; relógios do decisor UNKNOWN | 3 / 1 | revisão de licença dos dados pendente; Usar toy próprio nesta rodada evita depender da amostra real. |
| R019 | dez jogos A-League 2024/25 no README; tracking 10fps, detected/extrapolated, eventos e agregados de jogadores | retrospectivo; publicação/versão por decisão não comprovada | 3 / 1 | licença de código não substitui termos dos dados; Agregados com corte de minutos introduzem seleção; transferência de parâmetros não autorizada. |
| R020 | competições no artigo; catálogo detalhado não lido; eventos Wyscout | release retrospectivo | UNKNOWN / UNKNOWN | página principal inacessível; termos não resolvidos; Nenhum dataset importado. |
| R023 | Europa conforme documentação de adapter; Brasil não confirmado; ratings | data do rating não prova recebimento local | UNKNOWN / UNKNOWN | termos da fonte pendentes; Código/método pode transferir, parâmetros não. |
| R024 | ligas estrangeiras na documentação; Brasil não confirmado; xG/eventos de tiros | revisões e tempo de publicação UNKNOWN | UNKNOWN / UNKNOWN | scraper não executado; xG do próprio jogo é pós-fato; usar somente históricos admissíveis. |
| R025 | advanced stats removidos segundo aviso do provedor; disponibilidade depende do campo/data | mudança de fornecedor impede presumir continuidade | UNKNOWN / UNKNOWN | artigo detalhado 403; sem contorno; Não presumir que todo FBref saiu do ar nem que scraper tem mesmos dados antigos. |
| R027 | fixtures/resultados globais; Brasil/temporadas não auditados; JSON com identidade a conferir | geração posterior sem recibo de época | 3 / 1 | README declara CC0; conferir upstream e escopo; Reconstrução não pode ganhar known_at inventado. |
| R051 | histórico anunciado; liga/casa/período específicos UNKNOWN; odds, snapshots; formato/campos do plano não verificados | timeline histórica não é aceite local | UNKNOWN / UNKNOWN | nenhuma chamada; plano/custo/quotas UNKNOWN; Não consumir serviço sem orçamento. |
| R052 | catálogo comercial não auditado; jogadores, eventos, fixtures dependem do plano | PIT e revisions UNKNOWN | UNKNOWN / UNKNOWN | PUBLIC_EVIDENCE_ONLY; nenhum login; A marca não certifica disponibilidade do usuário. |
| R053 | conteúdo útil não renderizado; UNKNOWN | UNKNOWN | UNKNOWN / UNKNOWN | PUBLIC_EVIDENCE_ONLY; nenhum login; Inacessível na inspeção; não preencher cobertura por suposição. |
| R058 | calendário nacional anunciado para 2026; datas de competição, calendário; não lineups ou odds | página tem publicação/atualização; snapshots antigos completos não auditados | 3 / 2 | página pública lida; redistribuição não avaliada; Fonte de contexto; o início do ano competitivo mudou, investigar transporte de regimes sem usar desfechos. |



Escala de acesso: 0 indisponível/proibido; 1 restrito; 2 catálogo disponível; 3 amostra pública documentada; 4 cobertura necessária verificada; 5 dados autorizados acessados no escopo. PIT: 0 inadequado ao claim; 1 retrospectivo; 2 publicação conhecida incompleta; 3 versões e clocks parciais; 4 replay demonstrado; 5 recibos contemporâneos e linhagem demonstrados. UNKNOWN preserva falta de evidência; 1 não impede análise descritiva. Notas 3 dos datasets acima refletem disponibilidade documental, não ingestão brasileira validada.

**Contrato mínimo de qualquer fonte futura:** competição/edição, fixture e mapeamento versionado de times, jogadores/minutos quando aplicável, mando/local/período, campo/unidade, provedor/versão; event time, kickoff original/reprogramado, publication, revision, ingestion, processing e available_at; missingness, correções, custo/quota e direito de uso/redistribuição. Para quote: casa nominal, entidade, mercado/seleção/linha, odd decimal/moeda, status, snapshot e aceite separados. Não preencher relógio desconhecido com atraso inventado.

## Independência, negativos e exclusões

- penaltyblog, shin e implied implementam a mesma família matemática; são contrastes de código, não amostras econômicas independentes. T02 reproduz comportamento de dois módulos, não o solver Rust de shin.
- flumine e betfairlightweight pertencem ao mesmo ecossistema e compartilham transporte. footBayes e R033 compartilham autores. goalmodel/implied têm autor comum. socceraction/soccer_xg compartilham grupo e representação. Kloppy pode estar sob wrappers. Nenhum conjunto foi contado como replicação econômica independente.
- Resultados negativos: duas falhas de solver externo e dataclass permissivo em T02; variação não uniformemente favorável no paper R033; R035/R055 anunciam ausência de ganho, mas não foram replicados. Modelos não são descartados como falsos apenas por abstracts.
- worldfootballR foi adiado/rejeitado como **nova dependência crítica**, por estar arquivado; isso não invalida todo uso histórico. Dados pagos sem contrato, live betting, tipsters sem ledger auditável e imports não revisados não avançaram.
- Não houve sweep completo de issues, CVEs, releases e testes dos 15. Alguns candidatos têm apenas resumo/página renderizada; Nature e páginas de fornecedores falharam. Nenhuma tentativa de contornar acesso protegido. As lacunas restringem adoção, não impedem os testes sintéticos já elegíveis.
