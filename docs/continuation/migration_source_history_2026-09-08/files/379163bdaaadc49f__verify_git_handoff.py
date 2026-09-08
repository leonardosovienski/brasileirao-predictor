from pathlib import Path
import hashlib
import json
import re
import subprocess

REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
BACKUP = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor-sessoes\2026-09-07")
DOC = REPO / "docs/continuation"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def main():
    errors = []
    state = read(DOC / "review_2026-09-07/estado_final.json")
    for section in ("protected_sha256", "operational_sources_sha256"):
        for rel, expected in state[section].items():
            if sha((REPO / rel).read_bytes()) != expected:
                errors.append(f"changed_since_review:{rel}")
    receipt = read(DOC / "backup_receipt.json")
    manifest_bytes = (BACKUP / "BACKUP_MANIFEST.json").read_bytes()
    if sha(manifest_bytes) != receipt["manifest_sha256"]:
        errors.append("backup_manifest_hash")
    manifest = json.loads(manifest_bytes)
    for row in manifest["files"]:
        if sha((BACKUP / row["path"]).read_bytes()) != row["sha256"]:
            errors.append(f"backup_content:{row['path']}")
    artifacts = read(DOC / "versioned_artifacts.json")
    artifact_rows = artifacts["reports"] + artifacts["source_and_plans"]
    for row in artifact_rows:
        if sha(git("show", ":" + row["destination"])) != row["sha256"]:
            errors.append(f"staged_frozen_bytes:{row['destination']}")
    paths = git("diff", "--cached", "--name-only", "-z").decode().split("\0")
    paths = [p for p in paths if p]
    findings = []
    token_patterns = [
        r"\b(?:sk-(?:proj-)?|ghp_|github_pat_)[A-Za-z0-9_-]{20,}",
        r"\bAKIA[A-Z0-9]{16}\b",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r'''(?i)(?:api_?key|access_?token|secret_?key)\s*["']?\s*[:=]\s*["']([A-Za-z0-9_-]{24,})["']''',
    ]
    total_bytes = 0
    for path in paths:
        data = git("show", ":" + path)
        total_bytes += len(data)
        p = Path(path)
        if p.name.startswith(".env") or p.suffix in {".db", ".sqlite", ".sqlite3", ".log", ".jsonl"} or len(data) > 2_000_000:
            errors.append(f"unexpected_staged_private_or_large_file:{path}")
        text = data.decode("utf-8-sig")
        for pattern in token_patterns:
            for match in re.finditer(pattern, text):
                findings.append({"path": path, "line": text.count("\n", 0, match.start()) + 1, "kind": "credential_pattern"})
    tasks = read(DOC / "scheduled_paths_verified.json")
    if len(tasks) != 7:
        errors.append("active_task_count")
    for task in tasks:
        actions = task["Actions"]
        if isinstance(actions, dict):
            actions = [actions]
        for action in actions:
            if Path(action["WorkingDirectory"]).resolve() != REPO.resolve() or "Documents" in action["Execute"]:
                errors.append(f"task_depends_on_chat:{task['TaskName']}")
    for name in ("RETOMADA.md", "PROMPT_MELHORIA_LUCRO.md"):
        data = (DOC / name).read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", data):
            if "://" not in target and not (DOC / target).exists():
                errors.append(f"broken_link:{name}:{target}")
    result = {"protected_files_verified": len(state["protected_sha256"]),
              "reviewed_sources_unchanged": len(state["operational_sources_sha256"]),
              "persistent_files_reverified": len(manifest["files"]),
              "frozen_artifact_git_blobs_verified": len(artifact_rows),
              "staged_files": len(paths), "staged_bytes": total_bytes,
              "active_schedules_independent_of_chat": len(tasks),
              "credential_pattern_findings": findings, "errors": errors}
    out = Path(__file__).with_name("git_handoff_verification.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors or findings:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
