"""Read-only checks of outgoing Git objects and explicitly selected public files.

This is a bounded detector of recognizable secret patterns, not proof that an
arbitrary secret can never be present. It never reads private input files and
never prints matched values. Archived scripts are not executed by this check.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess


def git(repo, *args, data=None):
    return subprocess.check_output(['git', *args], cwd=repo, input=data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    publication = repo / 'docs/continuation/publication_2026-09-09'
    objects = git(repo, 'rev-list', '--objects', f'{args.base}..HEAD').decode().splitlines()
    names = {line.split(' ', 1)[0]: line.partition(' ')[2] for line in objects}
    packed = git(repo, 'cat-file', '--batch', data=('\n'.join(names) + '\n').encode())
    candidates = []
    offset = 0
    while offset < len(packed):
        end = packed.index(b'\n', offset)
        oid, kind, length = packed[offset:end].decode().split()
        start = end + 1
        finish = start + int(length)
        if kind == 'blob':
            candidates.append((f'{oid}:{names[oid]}', packed[start:finish]))
        offset = finish + 1
    for p in publication.rglob('*'):
        if p.is_file():
            candidates.append((p.relative_to(repo).as_posix(), p.read_bytes()))

    patterns = {
        'github_token': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
        'private_key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'aws_access_key': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
        'jwt': r'\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{20,}',
        'url_credentials': r'https?://[^\s/@:]+:[^\s/@]{8,}@',
    }
    secret_literal = re.compile(
        r'''(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*["']?\s*[:=]\s*["']([^"'\n]{12,})["']'''
    )
    findings = []
    seen = set()
    largest = 0
    for label, body in candidates:
        largest = max(largest, len(body))
        digest = hashlib.sha256(body).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        text = body.decode('utf-8', errors='replace')
        for name, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                findings.append({'file_or_blob': label, 'pattern': name,
                                 'line': text[:match.start()].count('\n') + 1})
        for match in secret_literal.finditer(text):
            value = match.group(1).lower()
            if any(marker in value for marker in ['synthetic', 'redacted', 'dummy', 'example',
                                                  'placeholder', 'test-', 'not-a-real', 'your_']):
                continue
            findings.append({'file_or_blob': label, 'pattern': 'literal_requiring_review',
                             'line': text[:match.start()].count('\n') + 1})

    manifest = json.loads((publication / 'manifest.json').read_text(encoding='utf-8'))
    verified = 0
    for entry in manifest['entries']:
        for rel in entry['git_paths']:
            body = (repo / rel).read_bytes()
            assert hashlib.sha256(body).hexdigest() == entry['sha256'], rel
        verified += 1
    protected = ['data', 'contracts', 'brasileirao_scripts', 'uv.lock', 'pyproject.toml', '.github']
    assert not git(repo, 'diff', '--name-only', f'{args.base}..HEAD', '--', *protected).strip()
    assert not git(repo, 'diff', '--name-only', '--', *protected).strip()
    assert largest < 50 * 1024 * 1024
    result = {'base': args.base, 'unique_contents_scanned': len(seen),
              'recognizable_secret_pattern_findings': findings,
              'scan_limit': 'Pattern detection only; private inputs not read',
              'source_mapping_hashes_verified': verified,
              'largest_outgoing_blob_or_public_file_bytes': largest,
              'protected_runtime_paths_unchanged': True,
              'archived_scripts_executed': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    if findings:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
