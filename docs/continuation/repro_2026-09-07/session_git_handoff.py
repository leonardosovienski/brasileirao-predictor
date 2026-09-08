"""Preserve this session outside the disposable chat and verify every copy."""
from pathlib import Path
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone

SOURCE = Path(r"C:\Users\Superleo13\Documents\Codex\2026-09-07\le")
BACKUP = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor-sessoes\2026-09-07")
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
DOC = REPO / "docs/continuation"
SKIP_ROOTS = {"brasileirao-predictor", "patch-verification", "resume-patch-check"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "numba_cache", "bin", "obj"}
SKIP_REVIEW = {"repo", "pytest_initial_tmp", "pytest_final_tmp", "pytest_release_tmp", "wheel", "wheel_final"}

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def copy_verified(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    before = sha(src)
    shutil.copy2(src, dst)
    after = sha(dst)
    if before != after or before != sha(src):
        raise RuntimeError(f"Copy changed or source unstable: {src}")
    return before

def main():
    if SOURCE == BACKUP or SOURCE in BACKUP.parents or BACKUP in SOURCE.parents:
        raise RuntimeError("Backup must be independent of the chat directory")
    copied, excluded = [], []
    for scope in ("outputs", "work"):
        root = SOURCE / scope
        for current, directories, files in os.walk(root, followlinks=False):
            cur = Path(current)
            for name in list(directories):
                child = cur / name
                skip = name in SKIP_DIRS or child.is_symlink()
                skip |= scope == "work" and cur == root and name in SKIP_ROOTS
                skip |= cur == root / "final_project_review" and name in SKIP_REVIEW
                if skip:
                    directories.remove(name)
                    excluded.append({"path": child.relative_to(SOURCE).as_posix(), "reason": "disposable clone/cache/build or link"})
            for name in sorted(files):
                src = cur / name
                rel = src.relative_to(SOURCE)
                if src.is_symlink() or name == ".coverage" or name.startswith(".env") or src.suffix in {".pyc", ".pyo"}:
                    excluded.append({"path": rel.as_posix(), "reason": "credential/cache/link"})
                    continue
                digest = copy_verified(src, BACKUP / rel)
                copied.append({"path": rel.as_posix(), "bytes": src.stat().st_size, "sha256": digest})
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(SOURCE), "backup_root": str(BACKUP), "operational_repo": str(REPO),
        "scope": "session outputs and research work, with private local data preserved opaquely; not a fresh live database backup",
        "credentials_copied": False, "source_files_removed": False,
        "files": copied, "excluded": excluded,
        "verified_files": len(copied), "verified_bytes": sum(r["bytes"] for r in copied),
    }
    write_json(BACKUP / "BACKUP_MANIFEST.json", manifest)
    receipt = {k: v for k, v in manifest.items() if k not in {"files", "excluded"}}
    receipt["manifest_sha256"] = sha(BACKUP / "BACKUP_MANIFEST.json")
    receipt["excluded_entries"] = len(excluded)
    write_json(BACKUP / "BACKUP_VERIFICATION.json", receipt)
    write_json(DOC / "backup_receipt.json", receipt)

    review = SOURCE / "outputs/REVISAO_FINAL"
    review_dest = DOC / "review_2026-09-07"
    public = []
    names = ["RESULTADO.md", "estado_final.json", "VALIDAR_REDIS_ISOLADO.ps1"]
    names += ["evidencias/" + n for n in (
        "METHODOLOGY_FINDINGS.md", "DIAGNOSTICO_QUALIDADE.md", "data_audit.md", "operational_code_review.md",
        "studies_reexecution.json", "diagnostics_quality_plan.json", "diagnostics_quality_results.json",
        "diagnostics_quality_verification.json", "pytest_release.json", "lint_release.json", "format_release.json",
        "types_final.json", "dotnet_build.json", "dotnet_unit.json", "wheel_final.json", "coverage_gate.json",
        "env_schema.json", "static_barriers_verified.json", "docker_probe.json", "scheduled_tasks_final.json")]
    for name in names:
        src = review / name
        dst = review_dest / Path(name).name
        digest = copy_verified(src, dst)
        public.append({"source": src.relative_to(SOURCE).as_posix(), "destination": dst.relative_to(REPO).as_posix(), "sha256": digest})
    sources = []
    for row in copied:
        rel = Path(row["path"])
        src = BACKUP / rel
        if rel.parts[0] != "work" or "retomada_backup" in rel.parts:
            continue
        if src.suffix in {".py", ".ps1"} or src.name in {"plan.json", "analysis_plan.json", "diagnostics_quality_plan.json", "config_frozen.yaml"}:
            if src.name == "ingest_sofascore_before.py":
                continue
            dst = DOC / "repro_2026-09-07" / Path(*rel.parts[1:])
            digest = copy_verified(src, dst)
            sources.append({"source": rel.as_posix(), "destination": dst.relative_to(REPO).as_posix(), "sha256": digest})
    write_json(DOC / "versioned_artifacts.json", {"reports": public, "source_and_plans": sources, "source_root": str(SOURCE), "persistent_root": str(BACKUP), "frozen_sources_relocated_without_edits": True})
    print(json.dumps({"backup": receipt, "versioned_reports": len(public), "versioned_sources_and_plans": len(sources)}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
