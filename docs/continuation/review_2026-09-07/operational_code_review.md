# Revisão independente das mudanças operacionais

Repositório examinado: `C:\Users\Superleo13\projetos\brasileirao-predictor`.
Escopo: launcher passivo, manifesto de jobs, parser histórico EXP001, contrato e classificador por turnos de 2026 e seus testes. A revisão encontrou três falhas reproduzíveis; as três foram corrigidas após autorização do agente principal.

## Achados corrigidos

### P1 — timeout deixava descendentes executando após o heartbeat de conclusão

`brasileirao_scripts/run_passive_task.py` executava o job com `subprocess.run(timeout=...)`. No Windows, o timeout mata o filho direto. Entretanto, `update_h9_fixtures.py` inicia ingestão, espelhamento e atualização de modelo em subprocessos próprios. Um descendente podia continuar executando e escrevendo depois de o wrapper informar `finished`, liberando a próxima execução do agendador para sobrepor trabalho.

Reprodução: uma árvore sintética em `tmp_path`, sem rede nem código de ingestão, deixou o neto escrever um marcador depois de o wrapper retornar 124. A regressão falhou antes da correção e passou depois.

Correção: `_run_command` mantém um `Popen` do pai vivo até encerrar sua árvore com `taskkill.exe /PID <pid-próprio> /T /F`. O comando usa lista de argumentos, `shell=False`, janela oculta e saída descartada. Nenhuma busca por nome de processo ou PID externo é usada. O timeout normal permanece 124; falha ao confirmar a limpeza é explícita como 125 / `timeout_tree_cleanup_failed`, preservando o último sucesso. A tentativa de limpeza e as esperas adicionais têm limites. Em plataformas diferentes de Windows, permanece o comportamento anterior de `subprocess.run`.

Limite operacional: se o próprio encerramento da árvore falhar, o wrapper reporta a falha e tenta encerrar o filho direto; não declara que descendentes foram limpos. Esse estado exige atenção operacional. A proteção `IgnoreNew` do agendador continua sendo um requisito externo; a revisão não alterou agendas.

Arquivos: `brasileirao_scripts/run_passive_task.py`, `tests/test_run_passive_task.py`, `tests/test_run_passive_process_tree.py`.

### P1 — erro de transporte do EXP001 podia imprimir a chave na traceback

`brasileirao_scripts/exp001_data_pilot.py::_get` já substituía a chave no corpo de respostas HTTP sem sucesso, mas deixava `requests.ConnectionError` e `requests.Timeout` escaparem. Essas exceções podem incluir a URL preparada com `apiKey`.

Reprodução: `requests.get` foi substituído por uma exceção com URL e credencial inteiramente sintéticas. A traceback retornada continha essa chave. Nenhuma requisição de rede ou credencial real foi usada.

Correção: `requests.RequestException` é convertida em mensagem genérica com `raise ... from None`, suprimindo também o contexto da exceção original. Os testes verificam a traceback completa para conexão e timeout, não apenas a mensagem principal. A lógica econômica e o parser de estados não foram modificados por essa correção.

Arquivos: `brasileirao_scripts/exp001_data_pilot.py`, `tests/test_exp001_cutoff_state_regression.py`.

### P2 — dez comandos restantes do manifesto apontavam para scripts inexistentes

O primeiro comando de `jobs.market-research.example.json` havia sido corrigido, mas os outros dez ainda usavam `scripts/...`, diretório ausente. Todos os respectivos arquivos existem em `brasileirao_scripts/...`. Essa era uma dívida anterior à correção do primeiro comando, e impediria executar os demais exemplos.

Correção: foram substituídos apenas os dez prefixos legados. IDs, parâmetros, timeouts, cadências e modos permaneceram iguais. Um teste de integridade agora exige que cada comando do manifesto aponte para um arquivo existente dentro de `brasileirao_scripts`.

Arquivos: `jobs.market-research.example.json`, `tests/test_market_research_jobs_manifest.py`.

## Itens revisados sem nova falha funcional encontrada

- O parser `_latest_at_cutoff` agora escolhe o último estado antes de verificar disponibilidade, rejeita suspensão e conflito de preço/atividade no mesmo instante e não ressuscita uma cotação anterior. Os casos sintéticos de suspensão, reativação, futuro, estado ambíguo e perna ausente passaram. Isso demonstra a correção do estado; não demonstra execução real, latência ou liquidez da cotação histórica.
- `role_for` mantém anos e rodadas oficiais, inclusive jogos adiados. Rejeita coerção de booleanos, textos ou rodadas inválidas para 2026.
- `eligibility_for_paper` exige booleanos explícitos, timestamps com fuso e decisão em T−1h posterior ao congelamento para classificar um sinal como futuro. A função documenta que as atestações de disponibilidade vêm do chamador; seu retorno não certifica execução em tempo real. Nenhum runner operacional é conectado automaticamente por esse classificador.
- O contrato por turnos permanece somente simulado, com capital desabilitado e sem candidato promovido. O SHA-256 atual, `4ea8c62a77cd07deb05ef6887318d811a9ed8204573a2839801bab2c1b9d5e68`, coincide com o hash final da decisão escrita.
- A precondição A1 do launcher compara a impressão digital da política/código, exige atestação explícita de rotação e existência da chave no ambiente. A revisão usou apenas arquivos sintéticos nos testes; não abriu o ledger A1 nem executou o fingerprint operacional.

## Verificação realizada

- Antes das correções: **3 regressões independentes falharam**, uma por achado.
- Depois das correções: **as mesmas 3 regressões passaram**, em 2,23 s.
- Suíte dirigida dos arquivos operacionais e do classificador: **152 testes passaram**, em 3,82 s.
- Ruff passou para os módulos e testes revisados.
- `git diff --check` passou; apenas avisos de normalização CRLF/LF foram emitidos.

Comando da suíte dirigida, usando o ambiente já instalado:

```powershell
& '.venv\Scripts\python.exe' -m pytest tests/test_run_passive_task.py tests/test_run_passive_process_tree.py tests/test_market_research_jobs_manifest.py tests/test_exp001_cutoff_state_regression.py tests/test_exp001_data_pilot.py tests/test_exp001_coverage_audit.py tests/test_season_2026_split.py -q -p no:cacheprovider
```

Os testes que invocam o launcher usual substituem seu executor por um mock. O único teste de árvore real cria scripts sintéticos em diretório temporário, sem importação de jobs operacionais, e o descendente tem duração curta. Os testes de transporte usam exceções sintéticas; o teste do manifesto apenas verifica arquivos de código.

## Como executar a suíte geral com segurança

`tests/conftest.py` somente ajusta `sys.path`; não isola o banco, a rede ou as credenciais. O `pytest.ini` exclui testes com marca `integration` por padrão, mas isso não é uma barreira contra efeitos colaterais de outros testes. Além disso, `ci_check.py` executa smokes de previsão quando encontra `data/matches.db`.

Por isso, a suíte geral deve usar uma cópia isolada do código atual, sobrepondo os arquivos novos desta revisão, sem copiar bancos, ledgers, snapshots, heartbeats ou credenciais operacionais. Usar os pacotes já instalados evita atualizações de dependências. As credenciais devem ser removidas somente do ambiente do processo de teste, e tentativas reais de conexão devem ser bloqueadas nesse processo. Não executar `ci_check` contra o repositório vivo. Testes de integração e serviços externos ficam separados e precisam de ambiente próprio.

O agente principal ficou responsável pela suíte geral, pela auditoria de tarefas/heartbeats e pela conferência final das impressões digitais. Esta revisão não antecipa o resultado desses trabalhos.

## Documentos e limites

Não foi encontrado `AGENTS.md` no repositório ou nos ancestrais verificados. Foram lidos `README.md`, `docs/A1_OU25_PHASE0_RUNBOOK.md`, `docs/COLLECTION_ONLY_HANDOFF.md`, `docs/decisions/2026-09-07-season-turn-split-paper.md`, `pytest.ini`, `pyproject.toml` e os arquivos de código/testes pertinentes.

Nenhuma coorte/ledger foi aberta, nenhuma agenda foi alterada, nenhum job operacional foi executado pela revisão e nenhuma rede, compra, pagamento ou aposta foi acionada. O README ainda contém uma afirmação histórica de que H14/H15 não foram ativadas; a conciliação documental com o estado das tarefas cabe ao agente principal que está verificando esse estado.

## Complemento — falso positivo na barreira estática de Elo

Na última verificação, `check_current_elo_containment()` classificou o capturador `persist_h14_prospective.py` como pesquisa retrospectiva porque seu caminho faltava na lista explícita de serving. A leitura independente da fonte confirmou que ele exige cache de modelo calculado até `now`, com idade máxima de 12 horas, e só persiste fixtures sem placar na janela `kickoff − 24h <= now < kickoff`. Trata-se de captura prospectiva do serving; essa classificação não é uma validação dos resultados científicos da coorte.

Foi acrescentado somente esse caminho exato à `SERVING_ALLOWLIST`, com justificativa temporal. `KNOWN_DEBT`, a expressão de detecção e os diretórios varridos permaneceram iguais. H14 e seus arquivos de dados não foram alterados.

O novo `tests/test_ci_current_elo_containment.py` copia apenas o texto da fonte para um diretório temporário e verifica a permissão do capturador. Outros três casos continuam rejeitados: novo replay em `research`, novo backtest em `brasileirao_scripts` e um arquivo com nome parecido terminado em `_copy`. **Os quatro testes passaram**, assim como Ruff. A execução somente da barreira estática no código operacional inspecionou 16 arquivos e terminou com **zero falhas e zero avisos**, sem executar smokes ou abrir bancos.

Arquivos adicionais para sobreposição: `brasileirao_scripts/ci_check.py` e `tests/test_ci_current_elo_containment.py`.
