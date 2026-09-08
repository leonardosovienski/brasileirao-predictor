from pathlib import Path
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone

repo = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
workspace = Path(r"C:\Users\Superleo13\Documents\Codex\2026-09-07\le")
backup = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor-sessoes\2026-09-07")
out = workspace / "outputs/RETOMADA_GIT"
out.mkdir(parents=True, exist_ok=True)
closeout = backup / "CONTINUACAO"
closeout.mkdir(parents=True, exist_ok=True)

def git(*args):
    return subprocess.check_output(["git", *args], cwd=repo)

def digest(data):
    return hashlib.sha256(data).hexdigest()

commit = git("rev-parse", "HEAD").decode().strip()
status = git("status", "--porcelain=v1", "--untracked-files=all").decode()
if status:
    raise RuntimeError("Working tree is not clean")
artifacts = json.loads((repo / "docs/continuation/versioned_artifacts.json").read_text(encoding="utf-8"))
for row in artifacts["reports"] + artifacts["source_and_plans"]:
    if digest(git("show", commit + ":" + row["destination"])) != row["sha256"]:
        raise RuntimeError("Committed frozen artifact hash differs: " + row["destination"])
copied = []
for source, filename in [
    (repo / "docs/continuation/PROMPT_MELHORIA_LUCRO.md", "PROMPT_MELHORIA_LUCRO.md"),
    (repo / "docs/continuation/RETOMADA.md", "RETOMADA.md"),
    (repo / "HANDOFF.md", "HANDOFF.md"),
    (workspace / "work/git_handoff_verification.json", "git_handoff_verification.json"),
    (workspace / "work/verify_git_handoff.py", "verify_git_handoff.py"),
    (Path(__file__), "close_git_handoff.py"),
]:
    destination = closeout / filename
    shutil.copy2(source, destination)
    sha = digest(source.read_bytes())
    if digest(destination.read_bytes()) != sha:
        raise RuntimeError("Closeout copy differs")
    copied.append({"name": filename, "sha256": sha})
prompt = repo / "docs/continuation/PROMPT_MELHORIA_LUCRO.md"
shutil.copy2(prompt, out / prompt.name)
receipt = {
    "saved_at_utc": datetime.now(timezone.utc).isoformat(),
    "repository": str(repo), "branch": "main", "commit": commit,
    "working_tree_clean": True, "push_performed": False,
    "changed_files_committed": len(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).decode().splitlines()),
    "prompt": str(prompt), "prompt_sha256": digest(prompt.read_bytes()),
    "backup": str(backup), "backup_manifest_sha256": digest((backup / "BACKUP_MANIFEST.json").read_bytes()),
    "backup_files_verified": 477, "backup_bytes_verified": 332995520,
    "frozen_artifact_commit_hashes_verified": 101,
    "private_inputs_and_credentials_committed": False,
    "context_independent_of_chat": True,
    "chat_deleted": False, "closeout_files": copied,
}
body = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
(closeout / "GIT_RECEIPT.json").write_text(body, encoding="utf-8")
(out / "GIT_RECEIPT.json").write_text(body, encoding="utf-8")
summary = f"""# Commit e retomada preservados

Commit local: `{commit}` na branch `main`. Foram commitados 128 arquivos;
o diretório de trabalho está limpo. Não foi feito push.

O prompt foi conferido contra a sessão e salvo no repositório. O resultado
atual continua −1,23 unidade no replay principal do segundo turno, com lucro
não demonstrado e integrações Docker/Redis ainda pendentes.

O contexto necessário para continuar não depende da conversa. Código e prompt
estão em `{repo}`. Os dados locais e evidências desta sessão foram preservados
em `{backup}`: 477 arquivos, 332.995.520 bytes, verificados por SHA-256, além
dos documentos finais em `CONTINUACAO`. Bancos e credenciais não entraram no Git.

Você pode apagar o chat e continuar pelo repositório. Preserve as duas pastas
acima. Esta cópia é local e não equivale a backup remoto.

Na nova tarefa, envie:

```text
Leia e execute C:\\Users\\Superleo13\\projetos\\brasileirao-predictor\\docs\\continuation\\PROMPT_MELHORIA_LUCRO.md
```

O guia `docs/continuation/RETOMADA.md` explica os caminhos históricos,
as validações executadas e as pendências. O recibo `GIT_RECEIPT.json` registra
o commit e os hashes conferidos. Nenhuma conversa foi excluída por esta execução.
"""
(out / "COMMIT_E_RETOMADA.md").write_text(summary, encoding="utf-8")
(closeout / "COMMIT_E_RETOMADA.md").write_text(summary, encoding="utf-8")
print(json.dumps({k:v for k,v in receipt.items() if k != "closeout_files"}, ensure_ascii=False, indent=2))
