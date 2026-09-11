# Experimentos, consumidores e reprodução

[PROTOCOL.json](PROTOCOL.json) foi escrito antes da execução: SHA-256 `0da6308b6754dc1c9307f6f28c20747fd555b55de3eebe5f3d8063054abce5b3`. G1 preservado; nenhum fitting ou tuning científico. Hipóteses/contratos/tolerâncias/limites estão no protocolo. [Origem do código](evidence/source_lineage.json).

## Usar o que foi entregue

No host atual, este comando é repetível: cria uma pasta nova por UTC, sem sobrescrever os exemplos ou runs anteriores. O nome do recibo também precisa ser novo.

```powershell
& 'C:/Users/leona/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' 'C:/BRASILEIRAO/brasileirao-predictor/docs/open_source_research/OSR-20260911-03/research/runner.py' use.py uso-002-receipt.json
```

O mesmo comando com `use-receipt.json` foi executado nesta sessão. Produziu [use-20260911T063408091434Z/COMPARACAO.md](evidence/use-20260911T063408091434Z/COMPARACAO.md), os manifests, comparison.json e goals.json. Leva entradas explícitas de examples/before.json, after.json e goals.json. O consumidor oferece `workflow.py run INPUT OUTPUT` e `workflow.py compare LEFT RIGHT`, além de `goals_demo.diagnose(parameters)`; o runner carrega as dependências isoladas com controles de I/O.

Python base gerenciado 3.13.12, NumPy 2.2.6, SciPy 1.15.3. Nenhuma instalação. Caminhos do Python/dependências/scratch são deste host, declarados em runner.py/child_boot.py. Em outra máquina, requer ambiente isolado correspondente e revisão desses caminhos, não import operacional ou instalação global automática. A cópia em outputs é entrega; o canônico continua no repositório.

O wrapper usa Job Object (768 MiB, um processo, atribuição verificada), timeout de 120s, ambiente allowlist, -I -S -B e hook Python contra rede/processos/I/O fora do escopo. A prova de timeout/probes da rodada 02 foi inspecionada, não repetida. Os recibos atuais confirmam atribuição e saídas sem timeout. Hook não é sandbox de SO contra código nativo malicioso. Nenhuma referência externa nova foi executada.

## T1 — composição 1X2

21 casos incluem controles completos/permutados/retries idênticos, seleção ausente/duplicada, partidas/regras/períodos/casas/snapshots incompatíveis, inversão, revisão tardia, suspensão, stale e clocks. Adota a última captura recebida, não remonta seleções de vintages distintos nem ressuscita snapshot incompleto. Idade <=300s sobre observed_at e snapshot_id/receipt comuns, tolerância de skew zero. Ordem 1/X/2. Underround recusa, justo explícito, proporcional primário; funções 02 preservadas.

Cinco mutantes de código real foram compilados e testados: snapshot, completude, regras, guarda de seleção e frescor. Cada um gerou ao menos uma admissão insegura detectada; não se usou apenas mudança de mensagem como prova. Isso não cobre todos os predicados ou autentica fontes. Evidência completa: [market-tests.json](evidence/market-tests.json).

## T2 — consumidor e falhas

A demo conserva três fixtures: antes uma admitida, uma incompleta e uma stale; depois duas admitidas e uma stale, por mudança explícita de INPUT. A cobertura de 1/3 para 2/3 não mede ganho do algoritmo. Probabilidades de SYN-1 mudam porque o preço/snapshot mudou; o comparador não atribui causa estatística. Mesmo universo/política são obrigatórios. Painel de model_scores tem market_scores_on_model_panel correspondente; não comparar silenciosamente subconjuntos distintos.

Sete verificações de falha/contrato passaram: sobrescrita, caminho fora do escopo, painel pareado, universo diferente, hash corrompido, política diferente e input alterado antes de publicar. Os diretórios tampered_copy/different_policy/failed_input_change são fixtures intencionais de teste, não evidência de estudos reais inválidos. O último preserva failure.json sem COMPLETE. [receipt-tests.json](evidence/receipt-tests.json).

Medida de workflow: um comando gera o fluxo completo em 4.711s nesta execução, incluindo startup e escrita. Não há medição de produtividade humana anterior nem alegação de aceleração de trabalho manual. O writer já existia; a contribuição é conectá-lo à admissão/scoring/comparação e ao relatório utilizável.

## T3 — custo e precisão

84 casos preregistrados: 81 com tolerância satisfeita e 3 recusas explícitas por limite de suporte 1024. Nos aprovados, erro máximo dos mercados 8.713708847e-07 <=1.0001e-6; referência com cauda <=1e-12 e limite 2048. Média, fatores DC, massa antes de normalizar, caudas, suporte e erro por caso registrados. Positividade, normalização, inversão de mando e entradas inválidas passaram no domínio ensaiado.

Fatores DC/PMFs invariantes deixam de ser recalculados em cada probe. Custo pareado, três repetições intercaladas por caso, warmup antes, mesma família e suporte. Comparador é o candidato 02, não o runtime fixo em 12.

| Parâmetros | Mediana 02 ms | Mediana 03 ms | Razão 02/03 |
|---|---|---|---|
| [1.4, 1.1, 0.1, -0.05] | 9.725500000058673 | 4.208299986203201 | 2.3110282137545957 |
| [2.5, 2, 0.5, -0.05] | 14.53320001019165 | 6.169100000988692 | 2.355805548274867 |
| [5, 4, 1, -0.02] | 28.560999999172054 | 18.020300005446188 | 1.584934767486679 |

Mediana das razões: 2.311. Meta experimental de >=2 foi atingida; isso não estabelece SLA operacional. O domínio do fitter alpha [1e-4,3] foi incluído, mas médias dos chamadores são ilimitadas/escalares de tempo restante: não há certificação universal. Um caso de médias 1e6 demonstrou SUPPORT_LIMIT sem vetor válido.

DNB: erro máximo condicionado 4.442593486e-05; denominador e bound conservador registrados. A tolerância incondicional não é prometida após divisão por probabilidade pequena. Reference/baseline e candidato compartilham SciPy, portanto não são três engines independentes. Não foram ampliados todos os mercados já testados em 02; esta rodada focou 1X2, BTTS, totais e DNB para a mudança delimitada.

## Recibos e limitações de execução

[execution_index.json](execution_index.json) lista comandos filhos exatos, cwd, versões evidenciadas, stdout/stderr, hashes e limites. Executados: test_market_workflow.py, test_goals.py, demo.py, test_receipts.py, goals_demo.py e use.py. Todos concluídos sem timeout. Houve duas buscas locais por arquivos inexistentes (telemetry.py/LICENSE e caminho inicial de soccerdata) e uma leitura de registry abortada por encoding cp1252; ajustadas para caminhos corretos/UTF-8 sem execução científica abortada. As tentativas não foram escondidas como resultados positivos.

O código dos consumers foi testado como entregue. artifacts.py é cópia exata da interface nativa; seus globals são restringidos no consumidor isolado. Isso não certifica o import ou o pipeline operacional original. Os manifests guardam código existente no momento da demo; arquivos de testes adicionados depois não reescrevem manifests antigos. Sem CI/pytest global, serviço, banco, quota, commit/push/merge ou operação financeira.
