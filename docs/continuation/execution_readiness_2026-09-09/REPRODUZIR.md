# Reprodução e continuidade — ER-20260909

Raiz técnica: `C:/BRASILEIRAO/work/execution-readiness-2026-09-09`.
Base `7f18d543891cb3e68bb82c0a0d9fb58f9a8f12c0`; commit final no recibo
`C:/BRASILEIRAO/AUDITORIA/EXECUTION_READINESS_2026-09-09.json`.
[Protocolo](PROTOCOL.md), [resultado](RESULTADO.md) e
[contrato de condições públicas](evidencias/execution_contract.json).

## Código e entradas

As duas rotinas ativas continuam nos caminhos conhecidos da automação:

- `C:/BRASILEIRAO/work/data-completion-2026-09-09/followup_capture.py`
- `C:/BRASILEIRAO/work/data-completion-2026-09-09/audit_followup.py`

Suas fontes versionadas ficam na pasta `reproducao` da rodada DC anterior.
A substituição afeta somente essa coleta independente, ainda não realizada.
Versões anteriores foram preservadas no Git e em `previous_active_scripts`
na área ER. A [continuidade DC](../data_completion_2026-09-09/CONTINUIDADE.md)
mantém fixture, corte, quotas, idempotência e proibição de apostas.

| Arquivo ou área ER | Evidência |
| --- | --- |
| `public_sources` | Cinco páginas primárias capturadas e manifesto com status/relógios/hashes |
| `tests-01-before-fix` | JUnit: cinco regressões falharam e sete testes passaram |
| `tests-02-after-fix` | Doze testes aprovados após a correção |
| `tests-03-complete` | Quinze casos aprovados com relógios e adiamento |
| `tests-04-integrated` | 153 testes isolados aprovados no conjunto de pesquisa |
| `checks` | Lint, formato, tipagem, auditoria isolada e idempotência |
| `existing_pilot_guard_check` | Reauditoria do primeiro payload DC sem alterar preço, hash ou relógios; não é observação nova |
| `engineering_checks.json` | Resultados dos checks e hashes dos executores/teste |
| `activation.json` | Cópia das versões novas para os caminhos ativos, com hashes anteriores e posteriores |

## Repetir os testes offline

Sem credenciais, APIs ou bancos, usando uma saída nova:

```powershell
$erOutput = Join-Path 'C:/BRASILEIRAO/work' ('er-tests-' + [guid]::NewGuid().ToString('N'))
& 'C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Scripts/python.exe' -I 'C:/BRASILEIRAO/work/execution-readiness-2026-09-09/validate_offline.py' $erOutput --full-research
if ($LASTEXITCODE -ne 0) { throw 'Ensaio falhou; preservar logs.' }
```

O teste novo está em `tests/test_followup_capture_contract.py`. O transporte
HTTP e a chave são sintéticos e a rede real é bloqueada pelo executor externo.
A auditoria de um payload real antigo foi executada separadamente com o próprio
guard da rotina, conservando seus clocks. O recibo deixa explícita essa origem.

`pyrightconfig.json` da área ER inclui explicitamente os dois executores;
a configuração geral do runtime exclui pesquisa e não serve para conferir
esse código. Usou-se Pyright 1.1.405, Ruff 0.12.12, pytest 8.4.2 e Python
3.13.12 no venv de pesquisa existente. Não houve instalação de dependências.

## A próxima captura continua futura

Fora da janela, `followup_capture.py` retorna WAITING sem ler a chave ou
consumir quota. Quando existir `followup/capture.json`, inclusive um corpo
inválido preservado, executar `audit_followup.py` em processo separado.
Erro HTTP sem corpo de captura fica no recibo de aquisição e não autoriza retry.
Campos ausentes não são preenchidos com zero nem convertidos em aprovação.

O acompanhamento às 19:57 de São Paulo é o mesmo da rodada DC; a janela de
11/09 antes das 20:00 não mudou. Computador e aplicativo precisam estar em
execução. Nenhum teste de rotina garante disponibilidade futura do fornecedor.
