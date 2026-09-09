# Reprodução offline da rodada PF-20260909

Base científica: f00304574044ab9d18aa3603abc538fbb3102c64 mais os novos fontes
identificados em `manifest.json`. Nenhum componente do runtime foi modificado.
Python 3.13.12; pytest 8.4.2; Ruff 0.12.12; Pyright 1.1.405. O ambiente completo
do predictor não é necessário para este diagnóstico puro de preço.

No computador desta rodada:

```powershell
Set-Location -LiteralPath 'C:\BRASILEIRAO\brasileirao-predictor'
$studyPython = 'C:\BRASILEIRAO\work\price-feasibility-2026-09-09\venv\Scripts\python.exe'
$studyWork = 'C:\BRASILEIRAO\work\price-feasibility-2026-09-09'
& $studyPython -I docs/continuation/price_feasibility_2026-09-09/run_offline.py --repository 'C:\BRASILEIRAO\brasileirao-predictor' --input "$studyWork\history.json" --output "$studyWork\run-reproduction"
if ($LASTEXITCODE -ne 0) { throw 'Falha na reprodução' }
& $studyPython -I docs/continuation/price_feasibility_2026-09-09/verify_decimal.py "$studyWork\history.json" "$studyWork\run-reproduction" "$studyWork\decimal-reproduction.json"
if ($LASTEXITCODE -ne 0) { throw 'Falha na conferência Decimal' }
& $studyPython -I docs/continuation/price_feasibility_2026-09-09/validate_offline.py 'C:\BRASILEIRAO\brasileirao-predictor' "$studyWork\validation-reproduction"
if ($LASTEXITCODE -ne 0) { throw 'Falha nos testes' }
```

Escolha diretórios/recibos novos. Não execute novamente avaliadores antigos,
coletores, scripts de governança ou restauração operacional. A saída principal
deve reproduzir o SHA de `summary.json`; timestamps de execução no manifesto
naturalmente mudam. Não comparar o hash do manifesto inteiro como se fosse
um fingerprint estatístico.

Se for necessário recuperar o insumo em outra máquina, confira o SHA do ZIP
e leia apenas esta entrada pelo módulo `zipfile` da biblioteca padrão:

```python
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

archive = Path('C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS/brasileirao-predictor-dados.zip')
destination = Path('C:/BRASILEIRAO/work/price-feasibility-2026-09-09/history.json')
member = 'projetos/brasileirao-predictor-sessoes/2026-09-07/price_strength_evaluation_2026-09-07/inputs/history.json'
with archive.open('rb') as stream:
    from hashlib import file_digest
    assert file_digest(stream, 'sha256').hexdigest() == '3860235c920fb0d6f7abfe916cf7ebdf5b1fa2a6e7679d7455bdf2d4fd415129'
with ZipFile(archive) as package:
    assert package.namelist().count(member) == 1
    raw = package.read(member)  # CRC conferido pelo ZipFile; nenhuma outra entrada é extraída.
assert sha256(raw).hexdigest() == '14153f7cbb348e9eef22a8e1c438757b1ef482951e2576d4a8381d7928e8e142'
destination.parent.mkdir(parents=True, exist_ok=True)
with destination.open('xb') as output:
    output.write(raw)
```

O ZIP e o insumo são privados. Não os coloque no Git. Não desserialize modelos,
não extraia `.env`/credenciais, não importe tarefas Windows e não abra bancos.
A verificação não depende de nova chamada a provedor. As três falhas públicas
estão preservadas em `source_attempts.json`; não representam ausência de odds.

Para repetir a tipagem nesta instalação, execute `pyright --project
C:/BRASILEIRAO/work/price-feasibility-2026-09-09/pyrightconfig-relative.json --stats`.
O recibo exige **quatro fontes conferidos**, sem depender da exclusão global de
`research` no pyproject. O arquivo da configuração está preservado no pacote
de entrega. Os caminhos `include` são relativos ao diretório da configuração.

Arquivos da implementação: `price_hurdle.py`, `tests/test_price_hurdle.py` e
os três scripts deste diretório. `quotes.py` é reutilizado sem alteração.
As regras e hashes pré-medida estão em `PROTOCOL.md` e
`MEASUREMENT_ADDENDUM.md`. Não altere esses arquivos para reclassificar esta
rodada como validação independente ou adaptar critérios ao resultado.
