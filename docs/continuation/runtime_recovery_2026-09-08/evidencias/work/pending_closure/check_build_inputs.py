"""Check the small Docker ignore policy against source paths and synthetic denied names."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
WORKTREE = ROOT.parent / 'integration-repo'


def expression(pattern):
    # The policy intentionally uses only literals, *, **, / and leading !.
    if any(char in pattern for char in '?[]\\'):
        raise ValueError('unsupported policy pattern; use the Docker engine for expanded syntax')
    pieces = []
    position = 0
    while position < len(pattern):
        if pattern[position:position + 3] == '**/':
            pieces.append('(?:.*/)?')
            position += 3
        elif pattern[position:position + 2] == '**':
            pieces.append('.*')
            position += 2
        elif pattern[position] == '*':
            pieces.append('[^/]*')
            position += 1
        else:
            pieces.append(re.escape(pattern[position]))
            position += 1
    return re.compile('^' + ''.join(pieces) + '$')


def main():
    policy = (REPO / '.dockerignore').read_bytes()
    patterns = []
    for line in policy.decode('utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        include = line.startswith('!')
        patterns.append((include, expression(line.removeprefix('!').strip('/'))))

    def included(path):
        components = path.split('/')
        parents = ['/'.join(components[:count]) for count in range(1, len(components) + 1)]
        allowed = True
        for include, pattern in patterns:
            if any(pattern.fullmatch(parent) for parent in parents):
                allowed = include
        return allowed

    required = ['README.md', 'pyproject.toml', 'uv.lock', 'constraints/shared-wheels.sha256',
                'dotnet/LineupWorker/LineupWorker.csproj', 'dotnet/LineupWorker/packages.lock.json',
                'dotnet/LineupWorker/appsettings.json', 'docker/vorp.json', 'docker/titularidade.json']
    # Enumerate only the code trees; never scan root/data or a protected artifact tree.
    source_paths = []
    for directory, extension in [('brasileirao_predictor', '*.py'), ('brasileirao_scripts', '*.py'),
                                 ('dotnet/LineupWorker', '*.cs')]:
        for path in (REPO / directory).rglob(extension):
            if any(part in {'obj', 'bin', '__pycache__'} for part in path.relative_to(REPO).parts):
                continue
            source_paths.append(path.relative_to(REPO).as_posix())
    actual_data_package = sorted(path for path in source_paths if path.startswith('brasileirao_predictor/data/'))
    assert 'brasileirao_predictor/data/xg_quality.py' in actual_data_package
    for path in required + source_paths:
        assert included(path), 'required build input excluded: ' + path
    synthetic_denied = ['data/sports.db', 'data/market.db', 'data/cohort-example.jsonl', '.env', '.env.production',
                        '.git/config', '.venv/lib/module.py', 'docs/archive/backup.json', 'outputs/result.json',
                        'work/receipt.json', 'brasileirao_predictor/data/example.db',
                        'brasileirao_predictor/.env', 'brasileirao_predictor/key.pem',
                        'brasileirao_predictor/__pycache__/x.pyc', 'dotnet/LineupWorker/bin/example.dll',
                        'dotnet/LineupWorker/obj/example.cs']
    for path in synthetic_denied:
        assert not included(path), 'unwanted context input included: ' + path
    ci_path = REPO / '.github/workflows/ci.yml'
    ci = yaml.load(ci_path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
    assert set(ci['jobs']) == {'python', 'dotnet', 'containers'}
    assert ci['jobs']['containers']['env']['COMPOSE_PROJECT_NAME'].startswith('brasileirao-ci-')
    assert not any('brasileirao-predictor-kernel-1' in step.get('run', '') or 'brasileirao-predictor-worker-1' in step.get('run', '')
                   for step in ci['jobs']['containers']['steps'])
    assert '--locked-mode' in (REPO / 'Dockerfile.worker').read_text(encoding='utf-8')
    (WORKTREE / '.dockerignore').write_bytes(policy)
    result = {'at_utc': datetime.now(UTC).isoformat(), 'passed': True, 'policy_sha256': hashlib.sha256(policy).hexdigest(),
              'policy_simulation_scope': 'Only literals, *, **, /, leading ! used by this .dockerignore; not a Docker build.',
              'required_source_count': len(source_paths), 'source_data_package_included': actual_data_package,
              'required_non_source_inputs': required, 'synthetic_excluded_paths': synthetic_denied,
              'protected_directories_scanned': False, 'ci_yaml_parsed': True, 'ci_executed': False,
              'docker_build_executed': False, 'worktree_policy_synchronized': True}
    with (ROOT / 'build_input_policy_review.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
