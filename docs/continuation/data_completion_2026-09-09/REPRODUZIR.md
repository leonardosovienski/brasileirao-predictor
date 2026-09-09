# Reproduzir DC-20260909

## Entradas e fontes preservadas

Área canônica: `C:/BRASILEIRAO/work/data-completion-2026-09-09`.
O Git contém código, protocolos, resumos e recibos sanitizados; dados brutos
de API e corpos de páginas ficam apenas na área local de pesquisa. O bundle
Git não é backup desses dados brutos: eles permanecem na pasta canônica e no
inventário com hashes. Pacotes antigos não contêm a aquisição nova.

| Arquivo/área local | Conteúdo |
| --- | --- |
| `universe.json` | 177 fixtures Jan–Jun/2026; SHA-256 6264b2a1b795928fdf0dc6476e311535a42fbc96c12caf5cf881777b7779caba |
| `acquisition.json`, `transport_repair.json`, `raw/` | 177 timelines finais verificadas; falha inicial preservada separadamente |
| `public_sources/football_data_bra_origin_csv.csv` | CSV oficial; SHA-256 ba3e9ea79ab4091b117a901f3914940cea07f1fe06de0deb57af5076f664ccb6 |
| `public_sources/manifest.json`, `extra_docs/public_sources/manifest.json` | Tentativas HTTP, clocks, status e hashes de fontes públicas, inclusive falhas |
| `prospective_pilot/` | Catálogos, fixture escolhido, três payloads, recibos e conta sanitizada |
| `closing-01/` | Freeze antes de labels 2025, eventos, contabilidade, resumos e manifestos |
| `admission-01/` | Auditoria temporal/estados e qualidade da fonte closing |
| `closing_independent_check.json` | Conferência aritmética separada com Fraction, pelo mesmo pesquisador |
| `tests-05/` | JUnit da execução final de 138 testes e log |
| `engineering_checks.json` | Recibo dos checks de integração e hashes do código |

Protocolos anteriores ao novo desempenho:

- [PROTOCOL.md](PROTOCOL.md): SHA-256 40b45152f77db425787739136a7092ee375a3ce0f34e07457b5cf43b6c10de21.
- [ACQUISITION_ADDENDUM.md](ACQUISITION_ADDENDUM.md): SHA-256 c684190305fbf8dae6375c1790641e8cf98eb2d2224af5aa0512d4c555393132.

Não alterar protocolos ou saídas para igualar uma nova execução. Novos recibos
terão clocks distintos. Compare escolhas, contagens, motivos e contabilidade,
não igualdade byte a byte de timestamps de execução.

## Scripts e isolamento

Scripts em [reproducao](reproducao/manifest.json) são cópias versionadas dos
executores locais. Os módulos puros ficam em
`brasileirao_predictor/research/price_strength`. Não usam banco, Redis ou API.

`run_closing.py`, `audit_results.py` e `validate_offline.py` limpam o ambiente,
bloqueiam rede, SQLite, subprocessos e leitura de dados operacionais/privados,
e limitam escrita às novas saídas. Os testes usam fixtures sintéticas;
o replay real usa somente o recorte de 2025 da fonte pública e não consulta
coortes protegidas. Variáveis de credenciais não são fornecidas aos executores.

Os scripts de aquisição consultam a chave de API de dados existente em processo
separado e não imprimem chave, URL autenticada ou corpo de conta privado.
Não executá-los como parte de teste, instalação ou reprodução offline.
`followup_capture.py` obedece à janela e à idempotência; sua auditoria roda
separadamente em `audit_followup.py`. [Continuidade](CONTINUIDADE.md).

## Comandos offline, sem repetir downloads

Python já instalado:
`C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Scripts/python.exe`.
Os executores recusam saída já existente. Para reproduzir os cálculos, criar
um diretório novo e copiar somente as entradas necessárias; nenhum banco,
credencial ou snapshot protegido participa. Não copiar o venv.

```powershell
$dcPython = 'C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Scripts/python.exe'
$dcSource = 'C:/BRASILEIRAO/work/data-completion-2026-09-09'
$dcReplay = Join-Path 'C:/BRASILEIRAO/work' ('dc-replay-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dcReplay | Out-Null
foreach ($dcItem in @('raw','public_sources','prospective_pilot','universe.json','acquisition.json','transport_repair.json','run_closing.py','audit_results.py','verify_closing_independently.py','validate_offline.py')) {
    Copy-Item -LiteralPath (Join-Path $dcSource $dcItem) -Destination $dcReplay -Recurse
}
& $dcPython -I (Join-Path $dcReplay 'run_closing.py')
if ($LASTEXITCODE -ne 0) { throw 'Closing falhou; preservar saída parcial.' }
& $dcPython -I (Join-Path $dcReplay 'audit_results.py')
if ($LASTEXITCODE -ne 0) { throw 'Auditoria falhou; preservar saída parcial.' }
& $dcPython -I (Join-Path $dcReplay 'verify_closing_independently.py')
if ($LASTEXITCODE -ne 0) { throw 'Conferência aritmética falhou.' }
& $dcPython -I (Join-Path $dcReplay 'validate_offline.py') 'C:/BRASILEIRAO/brasileirao-predictor' (Join-Path $dcReplay 'tests')
if ($LASTEXITCODE -ne 0) { throw 'Testes falharam.' }
```

Esperado: 380 linhas no cenário, 158 pares numéricos, 32 seleções condicionais,
348 abstenções, −9,24u e banca final 90,76u; histórico 177/177 arquivos,
zero execuções admitidas; piloto três capturas e zero pares de estado admitidos;
138 testes aprovados. O aviso de fonte compromete todas as 32 seleções;
reproduzir a conta não remove essa limitação.

Ruff e Pyright verificam explicitamente os três novos módulos e os quatro
arquivos de testes da rodada, com logs no recibo de engenharia. Não instalar
dependências, ligar operação ou executar avaliadores para repetir esses checks.
Não houve build/.NET/Redis/Compose, nem nova execução de CI remoto.
