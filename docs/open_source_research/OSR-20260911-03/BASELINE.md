# Baseline suficiente — OSR-20260911-03

HEAD `d9584af6deeec701cf8989349f22ab7e4b398249`, branch `main`, em `2026-09-11T06:25:45.645636+00:00`. Árvore inicial: `?? docs/open_source_research/`; nenhuma alteração tracked. Só existiam as rodadas 01 e 02. Ambas foram inspecionadas como linhagem, com fotografia de hashes de todos os arquivos em [baseline.json](baseline.json). Não foram refeitos seus benchmarks por releitura. Não foi consultado novo CI/remoto nesta rodada; o HEAD local é confirmado, o remoto desta sessão permanece não revalidado.

Instruções: C:/BRASILEIRAO/LEIA_PRIMEIRO.md e INSTRUCOES/PROXIMO_PROMPT_APOS_PUBLICACAO_2026-09-10.md; pontos de entrada README/HANDOFF/ESTADO_ATUAL/DATA_MAP/INDICE_DOCUMENTACAO e contratos RES. Busca por AGENTS.md não encontrou arquivo no clone. Trabalho solo, sem operação, fitting ou resultados protegidos. Comentários históricos de desempenho em config/protocolo foram incidentalmente visíveis na leitura de parâmetros; não foram usados como evidência nova, ajuste ou seleção. Nenhum arquivo de resultados dessas famílias foi aberto.

Mapa do fluxo, por caminhos inspecionados nesta rodada e referências históricas explícitas:

1. Providers / mapas PUB → curadoria versionada e envelopes: contratos RES inspecionados, sem coleta ou DB.
2. Identidade/clocks → PIT/contextual: presença atual de declarações de descanso/viagem/superfície/técnico; autenticidade da história não verificada.
3. Ratings/modelos → model.py/predict_match: médias exponenciais, NB/DC e grade; alpha do fitter [1e-4,3] herdado de inspeção 02. Médias não possuem teto global contratual. predict_remaining escala médias, portanto um piso arbitrário 0.05 não cobria todos os chamadores.
4. Mercados → market_pricer e odds_shop: grade/conversão existentes; consensus já exige mercados completos por casa, mas a exibição offline não é este contrato histórico T−60.
5. Filtros/avaliação → contracts RES e writer nativo: universo/abstenções devem permanecer; backtests protegidos não executados.
6. Decisão/simulação → pagamentos/caixa: resultados sintéticos 01 reaproveitados como históricos, não ampliados a lay/fills.
7. Relatório/consumidor → use.py novo: fluxo efetivamente executado apenas com exemplos SYN próprios.

Python: pacote __init__ injeta truststore quando disponível; foi evitado import operacional. predictor-core está declarado em pyproject e aparecem usos de contratos/telemetria/medição em busca delimitada por import. predictor-ops está declarado e há uso de redaction no payload sombra. Instalação/operação desses pacotes não verificada nesta sessão. O adapter ecosystem_plugin informa metadados/WAITING, não prova readiness.

Redis: kernel_cli requer DB absoluto e Redis e chama daemon/healthcheck; kernel_redis_v2 contém protocolo atômico e TTL de servidor. .NET LineupWorker/Program.cs configura Redis e serviços por ambiente. Presença de código não significa serviço ativo: nenhum desses caminhos foi iniciado ou consultado. Dependências/locks globais intactos.

[Inspeções atuais com hashes e linhas](evidence/internal_inspection.json). Protegidos: H14/H15/H9/A1, BE e acervos/avaliadores relacionados, apenas contratos/metadados. Inacessível/não verificado: contas pagas, payloads de fornecedores, estado operacional, cobertura real e CI global. Executado: exclusivamente scripts explícitos desta nova pasta via runner sanitizado.
