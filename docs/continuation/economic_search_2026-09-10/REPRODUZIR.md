# Reprodução BE-20260910

Tudo em C:/BRASILEIRAO. Não requer rede, banco, Redis ou credenciais. O estudo lê somente os bytes do CSV público DC de hash congelado; filtra temporadas antes dos demais campos. Não apontar a outros conjuntos ou coortes.

Ambiente efetivo: Python 3.13.12 do venv RI, já instalado; o executor econômico usa biblioteca padrão. O processo de pesquisa apaga variáveis de credenciais, recusa rede/subprocessos/SQLite e restringe arquivos à fonte/protocolo/código, bibliotecas e saída nova. Esse guard cobre o programa inspecionado, não constitui sandbox para código hostil. O source é montado via importlib, sem importar serving. Fontes públicas foram adquiridas separadamente, sem credenciais.

No PowerShell, a partir do repositório, escolhendo um nome de saída inexistente:

```powershell
& C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe -I -B C:/BRASILEIRAO/work/economic-search-2026-09-10/run_study.py run-NOVO
```

O arquivo `run_study.py` na entrega pode ser copiado para a mesma pasta work se necessário. O CLI direto do módulo aceita `--source`, `--protocol`, `--output-dir`; a execução com guard acima é preferida. Fonte e protocolo precisam corresponder exatamente aos hashes registrados. Não editar o protocolo para repetir resultados. Rodada executada: `run-01`,28,9 segundos, sem falha do cálculo ou ajuste posterior. Output é exclusivo, nunca sobrescrito.

Teste isolado:

```powershell
& C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe -I -B C:/BRASILEIRAO/work/economic-search-2026-09-10/run_isolated.py tests-NOVO test_economic_search.py
```

Dez casos passaram antes de abrir desfechos e novamente ao fechamento. Não são20 casos diferentes. A auditoria independente `audit_results.py` verifica SHA de todos os outputs, recalcula envelopes com Decimal40 dígitos e reconcilia cada fill/banca a partir do raw. Sua saída exclusiva já existe; para uma nova auditoria preserve o arquivo anterior e escolha outro nome de saída numa cópia do executor.

Ruff check e format dos dois arquivos novos e Pyright explícito foram aprovados. Pyright usa Node RI/tools/node.exe e venv/Lib/site-packages/pyright/dist/index.js, com `--pythonpath` para o venv real. O aviso de `.venv` ausente no checkout não significa ausência do ambiente RI usado. Uma primeira checagem apontou tupla de tamanho indeterminado no teste; corrigida anotação/construção, sem alterar o executor e os resultados.

Build inicial `python -m build --no-isolation` falhou porque hatchling não está instalado no venv RI. O build final reutiliza **offline** as dependências de build já disponíveis no cache uv IE, sem modificar o ambiente mínimo PF da captura:

```powershell
$env:UV_CACHE_DIR='C:/BRASILEIRAO/work/implementacao-2026-09-10/uv-cache'
$env:TEMP='C:/BRASILEIRAO/work/economic-search-2026-09-10'
$env:TMP=$env:TEMP
& C:/BRASILEIRAO/work/price-feasibility-2026-09-09/bootstrap/Scripts/uv.exe build --offline --no-python-downloads --python C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe --out-dir C:/BRASILEIRAO/work/economic-search-2026-09-10/dist-NOVO
```

O build não instala novo serving nem executa os scripts empacotados. A verificação do wheel/sdist confere os bytes do novo módulo contra o código efetivamente avaliado. Não foi repetida a suíte integral RI/IE nem executado CI remoto, .NET, Redis ou Compose nesta rodada econômica.

Fontes oficiais recuperadas e falhas estão em `sources`/`source-recovery` na pasta work/entrega; todos os recibos têm horário e SHA quando houve corpo recebido. Foram10 GETs diretos, zero API autenticada, compra ou nova conta. A inspeção web foi documental, sem acionar quotas. Não tratar redirecionamento, controle de idade ou URLError como prova de inexistência global de dados.

A pasta documental versiona protocolo, resumo, cobertura, conta independente e recibos. Outputs detalhados `envelopes.json`, `predictions.json`, `ledgers.json`, `matches.json` permanecem completos na entrega e no ZIP; não foram reduzidos aos226 candidatos. O source raw original permanece em DC e é incluído no backup da entrega para reprodução, sem interpretar temporadas2025/2026. O bundle Git e a entrega ZIP são verificados conforme o recibo final em C:/BRASILEIRAO/AUDITORIA/BUSCA_ECONOMICA_2026-09-10.json.

Os helpers DC conservaram SHA31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88 e ebce7ddeb384b347be4985b7a3812a1b83c7dfaceafdb3e2a6cb00f7e2d09a24. Coletor, auditor, agenda, fixture, janela e reserva não foram alterados.
