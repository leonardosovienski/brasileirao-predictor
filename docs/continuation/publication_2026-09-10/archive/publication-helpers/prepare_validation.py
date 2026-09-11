"""Prepare a portable, explicitly scoped publication check; no operational reads."""
import json
from pathlib import Path
import yaml

repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
res = Path('C:/BRASILEIRAO/work/resolution-2026-09-10')
dest = repo / 'tools/publication_validation'
dest.mkdir(exist_ok=True)
source = (res / 'run_isolated.py').read_text(encoding='utf-8')
source = source.replace("ROOT = Path(__file__).resolve().parent\nREPO = Path('C:/BRASILEIRAO/brasileirao-predictor')", "REPO = Path(__file__).resolve().parents[2]")
source = source.replace("out = (ROOT / sys.argv[1]).resolve()\n    if not out.is_relative_to(ROOT) or out == ROOT:\n        raise ValueError('new_output_inside_review_required')", "out = Path(sys.argv[1]).resolve()\n    if out == REPO or REPO.is_relative_to(out) or out.is_relative_to(REPO):\n        raise ValueError('new_output_outside_checkout_required')")
source = source.replace("tests = sys.argv[2:]\n    if not tests:\n        raise ValueError('explicit_tests_required')", "manifest = json.loads(Path(__file__).with_name('scope.json').read_text(encoding='utf-8'))\n    tests = manifest['tests']\n    if len(sys.argv) != 2 or not tests or any('..' in item or Path(item.split('::')[0]).is_absolute() for item in tests):\n        raise ValueError('reviewed_test_allowlist_required')")
source = source.replace("os.environ.update(TEMP=str(out), TMP=str(out),", "os.environ.update(HOME=str(out), USERPROFILE=str(out), TMPDIR=str(out), TEMP=str(out), TMP=str(out),")
source = source.replace("str(p).lower() in {'nul', '\\\\\\\\.\\\\nul'}", "p == Path(os.devnull).resolve()")
(dest / 'run.py').write_text(source, encoding='utf-8')
summary = json.loads((repo / 'docs/continuation/resolution_2026-09-10/evidence/python-validation.json').read_text())
tests = []
for run in summary['runs']:
    for item in json.loads((res / run / 'isolation.json').read_text())['tests']:
        if item not in tests:
            tests.append(item)
tests = [t for t in tests if '::' not in t or t.split('::')[0] not in tests]
(dest / 'scope.json').write_text(json.dumps({'scope': 'RES approved synthetic regression suites; not global CI or economic validation', 'tests': tests}, indent=2) + '\n')
workflow = (repo / '.github/workflows/ci.yml').read_text()
dotnet = workflow[workflow.index('  dotnet:'):]
dotnet = dotnet.replace('      - uses: actions/checkout@v7', '      - uses: actions/checkout@v7\n        with:\n          persist-credentials: false')
dotnet = dotnet.replace('    needs: [python, dotnet]', '    needs: [python, dotnet]')
dotnet = dotnet.replace('      - name: Enforce Worker line and branch coverage', '''      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: dotnet-validation
          path: |
            artifacts/dotnet-coverage
            ${{ runner.temp }}/brasileirao-runtime-lab
      - name: Enforce Worker line and branch coverage''')
dotnet = dotnet.replace('      - run: docker compose config --quiet', '''      - name: Isolate Compose configuration from operational paths
        run: |
          python tools/publication_validation/compose_config.py "$RUNNER_TEMP/compose-synthetic"
          echo "COMPOSE_FILE=$RUNNER_TEMP/compose-synthetic/compose.json" >> "$GITHUB_ENV"
      - run: docker compose config --quiet''')
dotnet = dotnet.replace('run: docker compose logs --no-color', 'run: docker compose logs --no-color > compose-validation.log')
dotnet += '''      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: compose-validation
          path: compose-validation.log
'''
header = '''name: Scoped synthetic publication validation

on:
  push:
    branches: ['publication-validation-*']
  workflow_dispatch:

permissions:
  contents: read

jobs:
  python:
    name: Synthetic Python ${{ matrix.python-version }}
    runs-on: ubuntu-latest
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.13', '3.14']
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@v7
        with:
          version: '0.12.1'
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install the locked dependency graph
        run: uv sync --locked --all-extras
      - name: Validate the reviewed synthetic allowlist
        run: .venv/bin/python -I -B tools/publication_validation/run.py "$RUNNER_TEMP/python-synthetic"
      - name: Validate publication tools
        run: |
          uv run ruff check tools/publication_validation
          uv run ruff format --check tools/publication_validation
      - name: Build distribution and inspect installed CLI
        run: |
          uv build
          uv venv "$RUNNER_TEMP/installed"
          uv pip install --python "$RUNNER_TEMP/installed/bin/python" --no-deps dist/*.whl
          test -f "$RUNNER_TEMP/installed/lib/python${{ matrix.python-version }}/site-packages/brasileirao_predictor/kernel_cli.py"
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: python-validation-${{ matrix.python-version }}
          path: |
            ${{ runner.temp }}/python-synthetic
            dist

'''
text = header + dotnet
text = text.replace('    name: .NET 10 build and test', '    name: Synthetic .NET 10 build and test\n    timeout-minutes: 20')
text = text.replace('    name: Compose build and health', '    name: Synthetic Compose build and health\n    timeout-minutes: 25')
(repo / '.github/workflows/publication-validation.yml').write_text(text, encoding='utf-8')
print(json.dumps({'tests': len(tests), 'workflow_created': True}))
