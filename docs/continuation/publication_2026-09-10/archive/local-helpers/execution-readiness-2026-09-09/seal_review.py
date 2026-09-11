"""Review links, changed scope, frozen hashes and active/versioned script parity."""
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
doc=repo/'docs/continuation/execution_readiness_2026-09-09'
dc=repo/'docs/continuation/data_completion_2026-09-09'
base='7f18d543891cb3e68bb82c0a0d9fb58f9a8f12c0'
modified=subprocess.check_output(['git','diff','--name-only'],cwd=repo,text=True).splitlines()
expected=['HANDOFF.md','README.md','docs/DATA_MAP.md','docs/ESTADO_ATUAL.md','docs/HISTORICAL_SOURCE_REGISTER.md',
          'docs/INDICE_DOCUMENTACAO.md','docs/PROMPT_PROXIMA_SESSAO.md','docs/continuation/RETOMADA.md',
          'docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md',
          'docs/continuation/data_completion_2026-09-09/reproducao/audit_followup.py',
          'docs/continuation/data_completion_2026-09-09/reproducao/followup_capture.py',
          'docs/continuation/data_completion_2026-09-09/reproducao/manifest.json']
assert set(modified)==set(expected)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==base
index=repo/'docs/INDICE_DOCUMENTACAO.md'
index.write_text(index.read_text(encoding='utf-8').replace('Rodada atual DC — resultados, evidências e continuidade',
    'Rodada DC — evidências e continuidade delimitada').replace('Os novos guias DC','Os guias DC/ER'),encoding='utf-8',newline='\n')
for name in ('PROTOCOL.md','ACQUISITION_ADDENDUM.md','RESULTADO.md'):
    frozen=subprocess.check_output(['git','show',base+':'+(dc/name).relative_to(repo).as_posix()],cwd=repo)
    assert frozen==(dc/name).read_bytes(),'frozen_DC_file_changed'
for name in ('followup_capture.py','audit_followup.py'):
    assert (dc/'reproducao'/name).read_bytes()==(Path('C:/BRASILEIRAO/work/data-completion-2026-09-09')/name).read_bytes()
for folder in (doc/'evidencias',dc/'reproducao'):
    values=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))['files']
    for name,digest in values.items():
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest
paths=[repo/p for p in expected if p.endswith('.md')]+list(doc.glob('*.md'))
links=[]
for path in paths:
    text=path.read_text(encoding='utf-8')
    if path.name=='HANDOFF.md':
        text=text.split('\n---\n')[0]
    for match in re.finditer(r'\[[^\]\n]*\]\(([^)\n]+)\)',text):
        target=match.group(1).strip().strip('<>')
        if re.match(r'^[a-zA-Z]+://',target) or target.startswith('#'):
            continue
        resolved=(path.parent/unquote(target.split('#')[0])).resolve()
        links.append({'source':str(path),'target':target,'exists':resolved.exists()})
missing=[r for r in links if not r['exists']]
assert not missing,missing
record={'reviewed_at':datetime.now(UTC).isoformat(),'base':base,'changed_existing_files':modified,
        'new_scope':['tests/test_followup_capture_contract.py','docs/continuation/execution_readiness_2026-09-09'],
        'frozen_DC_protocols_and_result_unchanged':True,'protected_runtime_or_contracts_changed':False,
        'active_script_parity':True,'local_links_checked':len(links),'missing_links':missing,
        'markdown_indexed':len(list(repo.rglob('*.md'))),'links':links}
(root/'review.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k in ('local_links_checked','missing_links','markdown_indexed','active_script_parity')}))
