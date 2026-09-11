"""Read installed distribution metadata and declared requirements; never import app code."""
import ast
import importlib.metadata as metadata
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
ri = Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09')
project = tomllib.loads((repo / 'pyproject.toml').read_text())
installed = {canonicalize_name(d.metadata['Name']): d for d in metadata.distributions() if d.metadata['Name']}
rows = []
for group, requirements in {'base': project['project']['dependencies'], **project['project']['optional-dependencies'],
                            'build': project['build-system']['requires']}.items():
    for raw in requirements:
        req = Requirement(raw)
        if req.marker and not req.marker.evaluate():
            continue
        dist = installed.get(canonicalize_name(req.name))
        rows.append(dict(group=group, requirement=raw, installed=None if dist is None else dist.version,
                         satisfied=dist is not None and (not req.specifier or dist.version in req.specifier)))
conflicts = []
for name, dist in installed.items():
    for raw in dist.requires or []:
        req = Requirement(raw)
        if req.marker and not req.marker.evaluate({'extra': ''}):
            continue
        dependency = installed.get(canonicalize_name(req.name))
        if dependency is None or (req.specifier and dependency.version not in req.specifier):
            conflicts.append(dict(package=name, version=dist.version, dependency=req.name,
                                  required=str(req.specifier), found=None if dependency is None else dependency.version))
inventory = json.loads((repo / 'docs/continuation/artifact_integrity_2026-09-10/evidence/source-inventory.json').read_text())
stdlib = sys.stdlib_module_names
mapping = metadata.packages_distributions()
imports = {}
for row in inventory:
    if row['review'] == 'protected_contract_only_no_execution' or not row['path'].endswith('.py'):
        continue
    if not row['path'].startswith(('brasileirao_predictor/', 'brasileirao_scripts/')):
        continue
    tree = ast.parse((repo / row['path']).read_text(encoding='utf-8-sig'))
    for node in ast.walk(tree):
        names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and not node.level and node.module else []
        for name in names:
            top = name.split('.')[0]
            if top not in stdlib and top not in {'brasileirao_predictor', 'brasileirao_scripts'}:
                imports.setdefault(top, []).append(row['path'])
missing = {name: sorted(set(paths)) for name, paths in imports.items() if name not in mapping}
env = {k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT', 'WINDIR', 'PATH', 'COMSPEC', 'PATHEXT'}}
for name in ('TEMP','TMP','DOTNET_CLI_HOME'):
    path = root / name.lower()
    path.mkdir(exist_ok=True)
    env[name] = str(path)
env.update(DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_CLI_TELEMETRY_OPTOUT='1', NUGET_PACKAGES=str(ri / 'nuget-packages'))
dotnet = subprocess.run([str(ri / 'dotnet-sdk/dotnet.exe'), '--list-sdks'], cwd=repo, env=env, capture_output=True, timeout=20)
receipt = dict(python=sys.version, executable=sys.executable, installed_distribution_count=len(installed),
    requirements=rows, transitive_base_conflicts=conflicts, missing_import_distribution_candidates=missing,
    dotnet_sdk=dotnet.stdout.decode().strip(), dotnet_exit_code=dotnet.returncode,
    scope='RI isolated venv and public allowed-source import inventory; no operational imports, secret config or API calls')
(root / 'dependencies.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False, indent=2))
