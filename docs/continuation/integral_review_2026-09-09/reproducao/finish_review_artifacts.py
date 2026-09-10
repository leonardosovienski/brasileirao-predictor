"""Prepare readable final documentation and a fixed reproduction manifest."""
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = Path('C:/BRASILEIRAO')
REPO = BASE / 'brasileirao-predictor'
RI = REPO / 'docs/continuation/integral_review_2026-09-09'

def clean(text):
    text = text.replace('research/dynamic_xg.py','research/price_strength/dynamic_xg.py')
    text = text.replace('DC prospective_pilot/calendar.json','DC prospective_pilot/fixture_catalog.json')
    text = text.replace('adapters/feature_builder.py','feature_builder.py')
    text = re.sub(r'(?<=\d)(?=arquivos|entradas|casos|testes|jogos|partidas|clubes|apostas|capturas|snapshots|eventos?\b|escolhas|linhas|timelines|pares|bytes|u\b|agosto|setembro|outubro|dezembro|passaram|aprovados|falhas|skip|GETs|URLs|HTTP|UTC|fontes|dependências|variáveis|questões|contratos|conta|consulta)', ' ', text)
    text = re.sub(r'(?<=\d)(?=faltam|sem|pulados)', ' ', text)
    text = re.sub(r'(?<=\d)(?=março|abril|maio|junho|julho)', ' ', text)
    for a,b in [('Todos177','Todos os 177'),('todos177','todos os 177'),('Os177','Os 177'),('os177','os 177'),('CSV2025','CSV 2025'),('jogos2025','jogos de 2025'),('partidas2025','partidas de 2025'),('labels2025','labels de 2025'),('labels2026','labels de 2026'),('desfechos2026','desfechos de 2026'),('Python3.13','Python 3.13'),('SDK.NET10','SDK .NET 10'),('.NET10','.NET 10'),('.NET69','.NET: 69'),('Ruff0.16','Ruff 0.16'),('Pyright1.1','Pyright 1.1'),('Core3.2','Core 3.2'),('Ops4.1','Ops 4.1'),('eDADOS','e DADOS'),('cobre12','cobre 12'),('de09/09','de 09/09'),('de10/09','de 10/09'),('noite de09','noite de 09'),('após12/09','após 12/09'),('ou12/09','ou 12/09'),('SQL externo','SQL externo')]:
        text=text.replace(a,b)
    # Commas in decimal numbers and URLs remain intact.
    text = re.sub(r',(?=[A-Za-zÀ-ÿ])', ', ', text)
    text = re.sub(r';(?=\S)', '; ', text)
    text = text.replace('fim de treino','fim de treino')
    return text

for path in list(RI.glob('*.md')) + [REPO/'README.md',REPO/'docs/ESTADO_ATUAL.md',REPO/'docs/continuation/RETOMADA.md',BASE/'LEIA_PRIMEIRO.md']:
    if path.name not in {'CHECKPOINT_INICIAL.md','PROTOCOLO.md'}:
        path.write_text(clean(path.read_text(encoding='utf-8')),encoding='utf-8')

# Only normalize the new portions of append-only historical entry guides.
for rel, boundary in [('HANDOFF.md', (ROOT/'previous-guides/HANDOFF.md').read_text(encoding='utf-8').split('\n',1)[1].strip()[:100]),('docs/DATA_MAP.md','## Armazenamento atual')]:
    path=REPO/rel
    text=path.read_text(encoding='utf-8')
    index=text.index(boundary)
    path.write_text(clean(text[:index])+text[index:],encoding='utf-8')
(BASE/'INSTRUCOES/PROXIMO_PROMPT_APOS_REVISAO_2026-09-09.md').write_bytes((RI/'PROXIMO_PROMPT.md').read_bytes())

repro=RI/'reproducao'
repro.mkdir(exist_ok=True)
names=['inventory.py','run_isolated.py','audit_data.py','recover_public.py','prepare_dotnet.py','run_dotnet.ps1',
       'NuGet.Config','pyrightconfig.json','package_smoke.py','test_isolation_boundary.py','consolidate_evidence.py',
       'write_reports.py','update_guides.py','finish_review_artifacts.py']
for name in names:
    shutil.copyfile(ROOT/name,repro/name)
manifest={name:hashlib.sha256((repro/name).read_bytes()).hexdigest() for name in names}
(repro/'manifest.json').write_text(json.dumps({'canonical_execution_root':str(ROOT), 'do_not_execute_from_documentation_copy':True,
    'scripts':manifest,'historical_generation_scripts_do_not_rerun_blindly':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Preserve the previous reproduction manifest rather than silently replacing its history.
shutil.copyfile(ROOT/'previous-active/manifest.json',RI/'evidence/previous-dc-manifest.json')
shutil.copyfile(ROOT/'package-smoke/receipt.json',RI/'evidence/package-smoke.json')
shutil.copyfile(ROOT/'baseline-test-selection.json',RI/'evidence/baseline-test-selection.json')
shutil.copyfile(ROOT/'source_inventory.json',RI/'evidence/source-inventory.json')

compact_logs=['baseline-failure-recheck.log','final-corrections.log','isolation-boundary.log','dotnet-build-03.log','dotnet-restore-03.log','dotnet-test-03.log',
              'ruff-ci-scope.log','ruff-format-ci-scope.log','pyright-fixed-version.log','pyright-explicit-02.log','package-build.log','package-smoke.log']
logdir=RI/'evidence/logs'
logdir.mkdir(exist_ok=True)
for name in compact_logs:
    shutil.copyfile(ROOT/name,logdir/name)

def markdown_links():
    failures=[]
    checked=0
    paths=list(RI.glob('*.md'))+[REPO/'README.md',REPO/'docs/ESTADO_ATUAL.md',REPO/'docs/continuation/RETOMADA.md',REPO/'docs/DATA_MAP.md',REPO/'docs/INDICE_DOCUMENTACAO.md',BASE/'LEIA_PRIMEIRO.md']
    for path in paths:
        for match in re.finditer(r'\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            target=match.group(1).split('#')[0].strip('<>')
            if not target or '://' in target or target.startswith('mailto:'):
                continue
            checked+=1
            if not (path.parent/target).resolve().exists():
                failures.append({'file':str(path),'target':target})
    result={'checked_local_links':checked,'failures':failures}
    (ROOT/'link-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if failures:
        raise ValueError(result)
    print(json.dumps(result))
markdown_links()
