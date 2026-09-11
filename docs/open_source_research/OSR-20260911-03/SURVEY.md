# Discovery complementar e decisões de transferência

O survey de 58 referências e 15 revisões focais permanece em OSR-01, com hashes de linhagem. Não foi reiniciado. A revisão atual aprofundou workflow, cache e produto completo e revalidou documentação dos três produtos de odds materiais ao gate. O catálogo completo anterior não é republicado como nova descoberta.

## R004 — soccerdata

API uniforme, cache e retry; cache sobrescrito não é arquivo PIT.

Versão: e120471e424a173e83e8aeeaaf4d954ab9d38ee4. C2. Apache-2.0; sem código transferido nesta rodada.

_common.py 275–312 e 490–534; tests/test_common.py 1–139 (mocks, cache hit, no_cache e no_store); não executado. Página de releases mostra v1.9.1; SHA local não é automaticamente esse tag.

Não adotar downloader para resolver relógios. Preservar writer versionado próprio; não executar mecanismos de contorno de acesso.

Issues abertas relatam CAPTCHA/locale; não reproduzidas. Lista inclui alegação de segurança em workflow, não auditoria nossa.

[Fonte 1](https://soccerdata.readthedocs.io/en/stable/intro.html); [Fonte 2](https://github.com/probberechts/soccerdata/issues); [Fonte 3](https://github.com/probberechts/soccerdata/releases)

## R049 — MLflow

RunData separa métricas, parâmetros e tags; tracking organiza artefatos e comparações.

Versão: v3.3.0 para código/teste focal; documentação de backend atual observada separadamente. C2. Apache-2.0; nenhuma dependência/código copiado.

mlflow/entities/run_data.py e tests/entities/test_run_data.py: serialização/hidratação e dicionários inspecionados, não executados. Não auditado o servidor nem toda UI.

Transferir ideia de comparação/linhagem ao writer existente. Sem necessidade demonstrada de instalar servidor/framework. Backend atual documenta SQLite padrão e filesystem legado; não repetir cegamente tutorial de mlruns como default universal.

Documentação corrente e tag focal têm versões distintas; issues gerais não varridas porque não haverá adoção da dependência.

[Fonte 1](https://github.com/mlflow/mlflow/blob/v3.3.0/mlflow/entities/run_data.py); [Fonte 2](https://github.com/mlflow/mlflow/blob/v3.3.0/tests/entities/test_run_data.py); [Fonte 3](https://mlflow.org/docs/latest/self-hosting/architecture/backend-store/); [Fonte 4](https://mlflow.org/docs/latest/ml/tracking)

## R059 — Hudl Statsbomb + Wyscout, plataforma comercial

Filtros salvos, seleção de jogadores, métricas ligadas a vídeo e configurações reutilizáveis.

Versão: Página pública observada em 11/09/2026; versão interna UNKNOWN. C0. Produto proprietário; PUBLIC_EVIDENCE_ONLY.

Somente documentação pública em português; não acessamos produto, dados, preço ou arquitetura. Objeto distinto de R016 (dataset aberto).

Padrão útil: contexto, filtro e evidência no mesmo fluxo. Não copiar scouting/vídeo/tracking sem necessidade/dados; não alegar horas poupadas localmente.

UNKNOWN para produto interno e condições da conta.

[Fonte 1](https://www.hudl.com/blog/hudl-statsbomb-video-wyscout-pt); [Fonte 2](https://pt.hudl.com/pt/products/wyscout/)

## Comparação das alternativas e custo de transferência

Para T1, validar só odds numéricas (N02/penaltyblog/shin/implied) não resolve a compatibilidade do mercado. O caminho próprio combina a admissão 02 e sua matemática já testada. O ganho é o contrato composto e seu consumidor, não superioridade de um solver externo. Não é necessária nova dependência.

Para T2, MLflow teria armazenamento/query/UI mais amplos, mas o projeto já possui writer imutável e uso solo em arquivos. Completar o comparador custa dois comandos públicos estreitos e dispensa servidor/migração. O cache de soccerdata economiza acessos, mas pode sobrescrever conteúdo; não serve como prova histórica por si. Mantivemos a proveniência própria.

Para T3, a análise de código local encontrou repetição de PMFs/parâmetros a cada probe. A ideia transferida é separar invariantes de trabalho variável, mantendo SciPy nbinom.sf. Não adotamos nbdtr diretamente: dispensável para o ganho demonstrado e seu contrato de parâmetros exigiria revisão própria. Referências goalmodel/penaltyblog continuam comparadores parciais de família, não oráculos independentes de todos os cálculos.

Licença: referências novas de MLflow/soccerdata não foram copiadas nem instaladas. Código transferido é do projeto/rodada anterior sob autorização de desenvolvimento local do usuário; ausência de LICENSE no clone não foi convertida em licença pública ampla. NumPy/SciPy permanecem dependências do ambiente isolado, sem distribuição de wheels ou alterações globais. Nenhum vídeo, dado comercial, peso ou fonte raw externo foi redistribuído.

Não copiar: scraping com contorno de bloqueios; cache como known_at; ranking de tipster sem ledger; troca indiscriminada de modelos; portabilidade de parâmetros estrangeiros; features esportivas já existentes; scouting/vídeo/tracking sem tarefa e licença. DEFER não refuta o método. Preservar soluções locais adequadas não prova vantagem universal.

A cobertura global é proporcional e acumulada: papéis estatísticos/modelos/eventos/risco constam no registro anterior e na matriz consolidada. Esta rodada não fez nova revisão completa de cada paper, issue ou produto. Duas ondas complementares encerraram discovery ao não mudar mais a carteira elegível. Produtos fechados e dados de eventos continuam menos verificados, sem adoção forçada.
