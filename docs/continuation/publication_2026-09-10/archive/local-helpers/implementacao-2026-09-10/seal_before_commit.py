"""Check protected helpers and publish immutable evidence fingerprints."""

import hashlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
doc=repo/'docs/continuation/implementation_2026-09-10'
ev=doc/'evidence'


def digest(p):
    raw=p.read_bytes()
    return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


expected={
    'followup_capture.py':'31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88',
    'audit_followup.py':'ebce7ddeb384b347be4985b7a3812a1b83c7dfaceafdb3e2a6cb00f7e2d09a24',
}
dc=Path('C:/BRASILEIRAO/work/data-completion-2026-09-09')
for name,sha in expected.items():
    assert digest(dc/name)['sha256']==sha,name
assert not (dc/'followup/receipt.json').exists()
assert not (dc/'followup/capture.json').exists()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()=='a7ded8800536a2b9ad845ebdb9f3ee1758d97861'
assert not subprocess.check_output(['git','diff','--name-only','--','docs/continuation/integral_review_2026-09-09','docs/continuation/data_completion_2026-09-09'],cwd=repo,text=True).strip()
workflow=yaml.load((repo/'.github/workflows/ci.yml').read_text(encoding='utf-8'),Loader=yaml.BaseLoader)
for job in ['python','dotnet']:
    assert workflow['jobs'][job]['services']['redis']['image']=='redis:8.2.9-alpine3.22@sha256:30abb90e62f14b737010746def3ba99cc79fe19dcdb3d37b41f21fc62e7da19d'
assert any('LINEUP_E2E_KERNEL_SCRIPT' in step.get('run','') for step in workflow['jobs']['dotnet']['steps'])
package=json.loads((root/'package-smoke-02/receipt.json').read_text(encoding='utf-8'))
assert package['cli_help_passed']==2 and not package['numeric_runtime_imported']
for name in ['ruff-final.log','ruff-format-final.log','pyright-default.log','pyright-explicit.log','build-python-final-02.log','package-smoke-final.log']:
    shutil.copyfile(root/name,ev/name)
shutil.copyfile(root/'package-smoke-02/receipt.json',ev/'package-smoke.json')
for name in ['run_isolated.py','run_capture_experiment.py','check_lab_boundaries.py','repair_register.py','capture_decision_before_universe.py','test_cold_start_preload_variant.py']:
    target=doc/'reproducao'/name;target.parent.mkdir(exist_ok=True)
    shutil.copyfile(root/name,target)
sources=['brasileirao_predictor/kernel_daemon.py','brasileirao_predictor/kernel_message.py','brasileirao_scripts/hotpath_smoke.py','brasileirao_scripts/coverage_report.py','brasileirao_predictor/research/price_strength/capture_decision.py','dotnet/LineupWorker.Tests/KernelCrossProcessTests.cs','.github/workflows/ci.yml','tests/test_capture_decision.py','tests/test_hotpath_cold_start.py']
sources += [p.relative_to(repo).as_posix() for p in (repo/'tools/runtime_lab').glob('*.py')]
seal={'created_at':datetime.now(UTC).isoformat(),'base_commit':'a7ded8800536a2b9ad845ebdb9f3ee1758d97861','protected_collectors_unchanged':expected,'followup_attempt_present':False,'sources':{p:digest(repo/p) for p in sources},'packages':{p.name:digest(p) for p in (root/'dist-final-02').iterdir()},'workflow_configuration_parsed':True,'remote_main_last_verified':'ac22c56c3318623e07a722f34d44dc6cd877ea37','remote_ci_for_new_revision_executed':False}
(ev/'seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
broken=[]
for p in [repo/'README.md',repo/'docs/ESTADO_ATUAL.md',repo/'docs/continuation/RETOMADA.md',*doc.glob('*.md')]:
    for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if link.startswith(('https://','http://','#')):
            continue
        if not (p.parent/link.split('#')[0]).resolve().exists():
            broken.append([str(p),link])
assert not broken,broken
manifest={p.relative_to(doc).as_posix():digest(p) for p in sorted(doc.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
(doc/'MANIFEST.json').write_text(json.dumps({'round':'IE-20260910','files':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'sealed_files':len(manifest),'protected_helpers_unchanged':True,'links_valid':True,'package_checked':True}))
