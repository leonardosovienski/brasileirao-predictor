"""Read-only syntax and migration checks for the runtime schema and CI."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

repo = Path.cwd()
for name in ('redis-protocol-v1.schema.json', 'redis-protocol-v2.schema.json', 'redis-fair-odds-v2.schema.json'):
    Draft202012Validator.check_schema(json.loads((repo / 'contracts' / name).read_text(encoding='utf-8')))
workflow = yaml.safe_load((repo / '.github/workflows/ci.yml').read_text(encoding='utf-8'))
for job, database in [('python', 14), ('dotnet', 15)]:
    value = workflow['jobs'][job]
    assert value['services']['redis']['ports'] == ['26380:6379']
    assert value['env']['LINEUP_TEST_REDIS_URL'] == f'redis://127.0.0.1:26380/{database}'
    assert any('LINEUP_TEST_REDIS_RUN_ID=' in step.get('run', '') for step in value['steps'])
smokes = [step['run'] for step in workflow['jobs']['containers']['steps']
          if 'hotpath_smoke' in step.get('run', '')]
assert len(smokes) == 2 and all('--synthetic-lineup' in command for command in smokes)
print('PASS: three JSON schemas and local CI v2 migration syntax/structure (not a remote CI run).')
