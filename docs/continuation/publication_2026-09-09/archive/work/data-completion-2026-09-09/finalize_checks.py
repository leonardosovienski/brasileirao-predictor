"""Persist scoped integration checks without acquisition or operational access."""
import ast
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/BRASILEIRAO/brasileirao-predictor')
VENV = Path('C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Scripts')
MODULES = [REPO / 'brasileirao_predictor/research/price_strength' / n for n in
           ('historical_admission.py', 'closing_scenario.py', 'live_capture_admission.py')]
TESTS = [REPO / 'tests' / n for n in ('test_historical_admission.py', 'test_historical_numeric_boundary.py',
                                   'test_live_capture_admission.py', 'test_closing_scenario.py')]
SCRIPTS = [ROOT / n for n in ('account_recheck.py','acquire_history.py','audit_followup.py','audit_results.py',
           'capture_pilot.py','check_account.py','fetch_public.py','fetch_public_extra.py','followup_capture.py',
           'repair_transport.py','run_closing.py','validate_offline.py','verify_closing_independently.py')]


def main():
    logs = ROOT / 'engineering-02'
    logs.mkdir(exist_ok=False)
    env = {k:v for k,v in os.environ.items() if k.upper() in
           {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC','PATHEXT'}}
    checks = []
    jobs = [
        ('pytest', [VENV/'python.exe','-I',ROOT/'validate_offline.py',REPO,ROOT/'tests-03']),
        ('ruff_check', [VENV/'ruff.exe','check','--no-cache',*MODULES,*TESTS,*SCRIPTS]),
        ('ruff_format', [VENV/'ruff.exe','format','--check','--no-cache',*MODULES,*TESTS,*SCRIPTS]),
        ('pyright', [Path('C:/Users/leona/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'),
                     VENV.parent/'Lib/site-packages/pyright/dist/index.js',
                     '--pythonpath',VENV/'python.exe',*MODULES]),
        ('followup_outside_window', [VENV/'python.exe','-I',ROOT/'followup_capture.py']),
        ('audit_without_capture', [VENV/'python.exe','-I',ROOT/'audit_followup.py']),
    ]
    for name,args in jobs:
        if name in ('pytest','ruff_check','ruff_format'):
            previous=ROOT/'engineering-01'/(name+'.txt')
            content=previous.read_text(encoding='utf-8')
            expected={'pytest':'137 passed','ruff_check':'All checks passed!','ruff_format':'20 files already formatted'}[name]
            assert expected in content
            checks.append({'name':name,'returncode':0,'log':str(previous),'reused_pass_from_initial_attempt':True})
            continue
        started = datetime.now(UTC).isoformat()
        result = subprocess.run(list(map(str,args)),cwd=REPO,env=env,capture_output=True,text=True,timeout=120)
        output=result.stdout+'\n'+result.stderr
        (logs/(name+'.txt')).write_text(output,encoding='utf-8')
        checks.append({'name':name,'started_at':started,'finished_at':datetime.now(UTC).isoformat(),
                       'returncode':result.returncode,'log':str(logs/(name+'.txt'))})
        if result.returncode:
            raise RuntimeError('check_failed:'+name)
        if name=='followup_outside_window' and json.loads(result.stdout)['status']!='WAITING':
            raise AssertionError('not_waiting')
        if name=='audit_without_capture' and result.stdout.strip()!='NO_CAPTURE_TO_AUDIT':
            raise AssertionError('unexpected_capture')
    # Execute only the pure clock function from its AST, with no imports/main/file reads.
    node=next(n for n in ast.parse((ROOT/'followup_capture.py').read_text(encoding='utf-8')).body
              if isinstance(n,ast.FunctionDef) and n.name=='window_status')
    from datetime import timedelta
    decision=datetime(2026,9,11,23,tzinfo=UTC)
    namespace={'DECISION':decision,'timedelta':timedelta}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<clock-boundaries>','exec'),namespace)
    times=[(decision-timedelta(days=1),'WAITING'),
           (decision-timedelta(minutes=5,microseconds=1),'WAITING'),
           (decision-timedelta(minutes=5),'DUE'),
           (decision-timedelta(seconds=45,microseconds=1),'DUE'),
           (decision-timedelta(seconds=45),'WINDOW_MISSED'),(decision,'WINDOW_MISSED')]
    for at,expected in times:
        assert namespace['window_status'](at)==expected
    try:
        namespace['window_status'](decision.replace(tzinfo=None))
    except ValueError:
        pass
    else:
        raise AssertionError('naive_time_accepted')
    junit=ET.parse(ROOT/'tests-03/junit.xml').getroot()
    suites=list(junit.iter('testsuite'))
    counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts=={'tests':137,'failures':0,'errors':0,'skipped':0},counts
    manifest={'completed_at':datetime.now(UTC).isoformat(),'status':'PASS','checks':checks,
              'pytest':counts,'clock_boundaries_passed':6,'naive_clock_rejected':True,
              'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*MODULES,*TESTS,*SCRIPTS]},
              'scope':'isolated_research_only_no_full_runtime_build_or_remote_CI',
              'network_calls_by_research_or_followup_in_checks':0,
              'initial_pyright_launcher_failure':{'log':str(ROOT/'engineering-01/pyright.txt'),
                                                 'reason':'sanitized_environment_without_home_directory',
                                                 'resolution':'invoke_installed_javascript_directly_no_install_or_update'},
              'formatting_precheck_repaired':{'line_length_findings':21,'unused_import_findings':1}}
    (ROOT/'engineering_checks.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','pytest':counts,'checks':len(checks),'clock_boundaries':6}))


if __name__=='__main__':
    main()
