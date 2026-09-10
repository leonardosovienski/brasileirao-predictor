# Reprodução e evidência — RI-20260909

Raiz de execução `C:/BRASILEIRAO/work/revisao-integral-2026-09-09`; repo `C:/BRASILEIRAO/brasileirao-predictor`. O recibo final identifica commit e hashes. Windows/Git/Codex/rede para baixar dependências são externos à pasta; venv não é pacote portável sem reinstalação. Todos os comandos abaixo têm escopo isolado, exceto o acesso a fontes públicas explícitas. Não executar avaliadores protegidos ou restaurar DB operacional.

## Instalação realizada

Python 3.13.12. `uv sync --all-extras --frozen --no-install-project` com `UV_PROJECT_ENVIRONMENT` apontando ao venv RI, `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, TEMP/TMP em RI e interpretador explicitamente indicado. 59 dependências do lock; Core 3.2.0 eOps 4.1.0 com hashes fixados. [Versões](evidence/environment.json).

SDK .NET 10.0.401 baixado do endereço oficial obtido em releases.json, SHA512 conferido antes de extrair em RI. `prepare_dotnet.py` criou cópia de código/contratos públicos em dotnet-work. `run_dotnet.ps1` usa NuGet. Config isolado, perfil/cache/TEMP em RI, restore locked, build Release --warnaserror e testes. Primeiras tentativas falharam por variáveis Windows necessárias removidas; a terceira manteve somente caminhos do sistema necessários e passou. Não iniciou worker/Redis; 41 testes de integração explicitamente pulados. [SDK](evidence/dotnet-sdk.json).

## Ensaios e reprodução dos dados

`run_isolated.py` deve receber um nome NOVO de saída seguido de arquivos de testes explícitos. Ele remove credenciais do ambiente, bloqueia rede/subprocessos/SQLite externo e escreve apenas nessa saída. Permite apenas socketpair de loopback criado pelo próprio stdlib e dois arquivos públicos exatos usados por testes existentes. O cliente nativo curl_cffi tem transporte real bloqueado. O harness não é um sandbox contra código hostil arbitrário: é uma barreira de efeitos para testes previamente inspecionados.

Lote amplo: lista congelada `baseline-test-selection.json`, 105 arquivos. Reconferência: `test_audit_fixes.py test_calibration_gate.py test_kernel_protocol.py test_kernel_runtime.py test_kernel_v2_runtime.py test_promotions_dataset.py test_integral_review_domain.py test_integral_review_admission.py`. Rodada final 68: `test_audit_fixes.py test_integral_review_event_backtest.py test_live_capture_admission.py test_followup_capture_contract.py test_integral_review_admission.py test_integral_review_domain.py test_temporal_policy.py test_temporal_replay.py`. JUnit e tentativas mantidos em pastas distintas. [Contagens por rodada e IDs únicos](evidence/tests.json).

`audit_data.py` verifica somente a allowlist DC, hashes, universo, clocks, catálogos e o CSV filtrado 2025. Nunca abre DB ou desfechos de 2026. Não rerodar sem motivo: saída existente é protegida por criação exclusiva. `data-audit-02` é a execução bem-sucedida após reconhecer o reparo de transporte já registrado em DC. Não é uma nova validação econômica. [Conta compacta](evidence/closing-summary.json).

`recover_public.py` foi executado uma vez por URL. Raw/recibos locais em public-sources. Não repetir downloads de odds, consultas autenticadas ou lotes íntegros; não reutilizar esse script como autorização futura automática.

## Checks de engenharia

Ruff 0.16.6: `ruff check brasileirao_predictor brasileirao_scripts tests`; `ruff format --check` nos mesmos diretórios: 390 arquivos. A expansão `ruff check .` encontrou 805 questões em cópias/documentação/scripts históricos fora da CI; log preservado, sem reformatar resultados congelados. O executor audit_followup alterado recebe check próprio. Não tratar esse resultado como lint global limpo.

Pyright 1.1.411 fixo: executar `tools/node.exe venv/Lib/site-packages/pyright/dist/index.js --pythonpath venv/Scripts/python.exe` no repo. O projeto exclui research da análise padrão; por isso há também `--project RI/pyrightconfig.json` cobrindo os três módulos puros de price_strength e o auditor alterado. Não usar PYRIGHT_PYTHON_FORCE_VERSION=latest. A tentativa inicial está preservada e não compõe aprovação.

`uv build --out-dir RI/dist` criou sdist e wheel. `package_smoke.py` extrai wheel em nova pasta sem .env/SQLite, confere import a partir dele e executa apenas `brasileirao-predict --help`, sem rede/DB. Não demonstra previsões com dados reais. Após atualizar os guias, dist-final foi construído e package_smoke_final.py verificou novamente a ajuda e a igualdade byte a byte dos quatro módulos alterados com o checkout; recibo em evidence/package-smoke-final.json. O CLI ainda contém texto legado de seleções internacionais; serving não é oferta executável.

CI remoto da **base** ac22c56: [run 34419406215](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34419406215), success confirmado via API pública. Não atribuir esse CI às alterações RI. CI integral envolve avaliadores e serviços fora do escopo desta rodada; os checks usados para integrar RI são os isolados declarados.

## Ativação e recuperação

Só o auditor offline da captura independente foi atualizado no caminho ativo, após testes e checagem de ausência de execução concorrente. Versão anterior em RI/previous-active. Coletor SHA256 `31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88`, inalterado. [Ativação](evidence/activation.json). O manifesto de reprodução atual recebe o novo hash e guarda referência ao anterior.

No fechamento, criar bundle Git com nome novo em `C:/BRASILEIRAO/BACKUPS`, verificar, clonar em bare novo sob RI e executar fsck. Não criar checkout operacional, importar tarefas ou abrir bancos. A entrega em ENTREGAS é conferida por hashes contra o diretório de revisão. Esses atos comprovam recuperação do Git e cópia de artefatos, sem afirmar recuperação completa de serviços/dados privados.
