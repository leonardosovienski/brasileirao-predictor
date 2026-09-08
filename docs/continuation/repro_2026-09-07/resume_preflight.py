import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
WORK = Path(__file__).resolve().parent
BACKUP = WORK / 'retomada_backup'
sys.path.insert(0, str(ROOT))
from brasileirao_scripts.a1_phase0 import _fingerprint
from brasileirao_predictor.collector_a1 import OddsPapiClient, quota_status

BACKUP.mkdir(exist_ok=False)
protected = [
    'config.yaml', 'pyproject.toml', 'uv.lock', 'data/trials.json',
    'contracts/a1-ou25-phase0-policy.json', 'brasileirao_scripts/persist_h14_prospective.py',
    'brasileirao_scripts/persist_h15_prospective.py', 'brasileirao_predictor/model.py',
    'brasileirao_predictor/ratings.py', 'brasileirao_predictor/cron_update_models.py',
    'brasileirao_scripts/collect_odds_a1.py', 'brasileirao_predictor/collector_a1.py',
    'schemas/odds_snapshot_v1.json', 'data/team_aliases.json',
]
hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in protected}
for name in protected + ['HANDOFF.md','jobs.market-research.example.json']:
    dest = BACKUP / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/name, dest)
for directory in ['data/a1_phase0','data/odds_snapshots','data/collector_state','data/collector_metrics']:
    shutil.copytree(ROOT/directory, BACKUP/directory)
for source in (ROOT/'data/research').glob('h1[45]*'):
    if source.is_file():
        dest = BACKUP/'data/research'/source.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source,dest)
with sqlite3.connect((ROOT/'data/matches.db').as_uri()+'?mode=ro',uri=True) as source:
    with sqlite3.connect(BACKUP/'data/matches.db') as target:
        source.backup(target)
saved = json.loads((ROOT/'data/a1_phase0/fingerprint.json').read_text(encoding='utf-8'))
current = _fingerprint()
rotation = json.loads((ROOT/'data/collector_metrics/key_rotation_attestation.json').read_text(encoding='utf-8'))
account = {'status':'NOT_CHECKED'}
try:
    count,limit = quota_status(OddsPapiClient().account())
    account = {'status':'READ_ONLY_OK','request_count':count,'request_limit':limit,'reserve':20,
               'remaining_above_reserve': max(0,limit-count-20)}
except Exception as exc:
    account = {'status':'FAILED_CLOSED','error_type':type(exc).__name__}
report = {
    'observed_at':datetime.now(UTC).isoformat(),
    'backup_created':True,'backup_path':str(BACKUP),'protected_sha256':hashes,
    'a1_fingerprint_matches':saved.get('fingerprint')==current['fingerprint'],
    'a1_fingerprint':current['fingerprint'],
    'rotation_attested':rotation.get('rotated') is True,
    'account':account,'scientific_metrics_computed':False,
}
(WORK/'resume_preflight_result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='protected_sha256'}))
